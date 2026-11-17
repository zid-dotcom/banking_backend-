import secrets
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.core.notifications import add_member_notification
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.cash_reconciliation import CashReconciliation
from app.models.cash_transaction import CashTransaction
from app.models.savings_account import SavingsAccount
from app.models.savings_scheme import SavingsScheme
from app.models.staff import Staff
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.cash_transaction import (
    CashDepositCreate,
    CashDepositOut,
    CashierAccountLookupOut,
    CashWithdrawalCreate,
    CashTransactionOut,
)

staff_router = APIRouter(prefix="/staff", tags=["Staff - Cash Transactions"])
branch_admin_router = APIRouter(
    prefix="/branch-admin/cash-transactions",
    tags=["Branch Admin - Cash Transactions"],
)
superadmin_router = APIRouter(
    prefix="/superadmin/cash-transactions",
    tags=["Superadmin - Cash Transactions"],
)
member_router = APIRouter(
    prefix="/member/savings-accounts",
    tags=["Member - Savings Account Transactions"],
)

MAX_ACCOUNT_BALANCE = Decimal("999999999999.99")


def require_open_cash_day(db: Session, user: User) -> CashReconciliation:
    report = (
        db.query(CashReconciliation)
        .filter(
            CashReconciliation.cashier_user_id == user.id,
            CashReconciliation.branch_id == user.branch_id,
            CashReconciliation.status == "open",
        )
        .with_for_update()
        .first()
    )
    if not report:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Open your cash day and record the starting cash before processing transactions",
        )
    return report


def get_cashier_role(db: Session, user_id: int) -> StaffRole:
    row = (
        db.query(StaffRole)
        .join(Staff, Staff.staff_role_id == StaffRole.id)
        .filter(
            Staff.user_id == user_id,
            StaffRole.is_deleted == False,
        )
        .first()
    )
    if not row or row.name.strip().casefold() not in {"cashier/teller", "cashier"}:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only Cashier/Teller staff can record cash transactions",
        )
    return row


def generate_receipt_number(db: Session) -> str:
    for _ in range(20):
        receipt_number = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
        exists = db.query(CashTransaction.id).filter(
            CashTransaction.receipt_number == receipt_number
        ).first()
        if not exists:
            return receipt_number
    raise HTTPException(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Could not generate a unique cash transaction receipt number",
    )


def transaction_query(db: Session):
    member_user = aliased(User)
    cashier_user = aliased(User)
    query = (
        db.query(
            CashTransaction,
            SavingsAccount,
            member_user,
            cashier_user,
            Branch,
        )
        .join(SavingsAccount, CashTransaction.account_id == SavingsAccount.id)
        .join(member_user, SavingsAccount.member_id == member_user.id)
        .join(cashier_user, CashTransaction.staff_user_id == cashier_user.id)
        .join(Branch, CashTransaction.branch_id == Branch.id)
    )
    return query


def to_transaction_out(row) -> CashTransactionOut:
    transaction, account, member_user, cashier_user, branch = row
    return CashTransactionOut(
        id=transaction.id,
        receipt_number=transaction.receipt_number,
        account_id=account.id,
        account_number=account.account_number,
        member_code=member_user.user_code,
        member_name=member_user.full_name,
        transaction_type=transaction.transaction_type,
        amount=transaction.amount,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        branch_id=branch.id,
        branch_name=branch.name,
        branch_code=branch.branch_code,
        ifsc_code=branch.ifsc_code,
        cashier_user_id=cashier_user.id,
        cashier_code=cashier_user.user_code,
        cashier_name=cashier_user.full_name,
        notes=transaction.notes,
        created_at=transaction.created_at,
    )


def list_transactions(
    db: Session,
    *,
    branch_id: int | None,
    staff_user_id: int | None,
    account_number: str | None,
    skip: int,
    limit: int,
) -> List[CashTransactionOut]:
    query = transaction_query(db)
    if branch_id is not None:
        query = query.filter(CashTransaction.branch_id == branch_id)
    if staff_user_id is not None:
        query = query.filter(CashTransaction.staff_user_id == staff_user_id)
    if account_number:
        query = query.filter(SavingsAccount.account_number == account_number.strip())
    rows = (
        query.order_by(CashTransaction.created_at.desc(), CashTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_transaction_out(row) for row in rows]


@staff_router.post(
    "/cash-deposits",
    response_model=CashDepositOut,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_deposit(
    data: CashDepositCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    require_open_cash_day(db, current_user)

    account = (
        db.query(SavingsAccount)
        .filter(
            SavingsAccount.account_number == data.account_number,
            SavingsAccount.branch_id == current_user.branch_id,
        )
        .with_for_update()
        .first()
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found in your branch")
    if account.status not in {"active", "awaiting_initial_deposit"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "This savings account cannot receive deposits")

    scheme = db.query(SavingsScheme).filter(SavingsScheme.id == account.savings_scheme_id).first()
    if not scheme:
        raise HTTPException(status.HTTP_409_CONFLICT, "Savings account scheme not found")

    balance_before = account.balance
    balance_after = balance_before + data.amount
    if balance_after > MAX_ACCOUNT_BALANCE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Account balance exceeds the allowed limit")

    was_awaiting_initial_deposit = account.status == "awaiting_initial_deposit"
    if was_awaiting_initial_deposit and balance_after >= scheme.min_opening_balance:
        account.status = "active"

    if account.status == "awaiting_initial_deposit":
        remaining_opening_deposit = max(
            scheme.min_opening_balance - balance_after,
            Decimal("0.00"),
        )
        message = (
            f"Minimum opening amount is INR {scheme.min_opening_balance:.2f}. "
            f"You deposited INR {data.amount:.2f}. "
            f"INR {remaining_opening_deposit:.2f} more is needed to activate your account."
        )
        notification_title = "More deposit needed to activate account"
    else:
        remaining_opening_deposit = Decimal("0.00")
    if account.status == "active" and was_awaiting_initial_deposit:
        message = (
            f"You deposited INR {data.amount:.2f} and reached the minimum opening "
            f"amount of INR {scheme.min_opening_balance:.2f}. Your account is now active."
        )
        notification_title = "Savings account is now active"
    elif account.status == "active" and not was_awaiting_initial_deposit:
        message = (
            f"Cash deposit of INR {data.amount:.2f} received. "
            f"New balance: INR {balance_after:.2f}."
        )
        notification_title = "Cash deposit received"

    transaction = CashTransaction(
        receipt_number=generate_receipt_number(db),
        account_id=account.id,
        branch_id=account.branch_id,
        staff_user_id=current_user.id,
        transaction_type="deposit",
        amount=data.amount,
        balance_before=balance_before,
        balance_after=balance_after,
        notes=data.notes.strip() if data.notes and data.notes.strip() else None,
    )
    account.balance = balance_after
    db.add(transaction)
    add_member_notification(
        db,
        recipient_id=account.member_id,
        notification_type="cash_deposit_received",
        title=notification_title,
        message=f"{message} Account: {account.account_number}. Receipt: {transaction.receipt_number}.",
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Deposit could not be recorded due to a transaction conflict",
        ) from error

    db.refresh(transaction)
    row = transaction_query(db).filter(CashTransaction.id == transaction.id).first()
    transaction_out = to_transaction_out(row)
    return CashDepositOut(
        **transaction_out.model_dump(),
        account_status=account.status,
        minimum_opening_balance=scheme.min_opening_balance,
        remaining_opening_deposit=remaining_opening_deposit,
        message=message,
    )


@staff_router.post(
    "/cash-withdrawals",
    response_model=CashTransactionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_withdrawal(
    data: CashWithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    require_open_cash_day(db, current_user)

    account = (
        db.query(SavingsAccount)
        .filter(
            SavingsAccount.account_number == data.account_number,
            SavingsAccount.branch_id == current_user.branch_id,
        )
        .with_for_update()
        .first()
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found in your branch")
    if account.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only active savings accounts can withdraw cash")

    scheme = db.query(SavingsScheme).filter(SavingsScheme.id == account.savings_scheme_id).first()
    if not scheme:
        raise HTTPException(status.HTTP_409_CONFLICT, "Savings account scheme not found")

    balance_before = account.balance
    withdrawable_balance = max(balance_before - scheme.lock_in_amount, Decimal("0.00"))
    if data.amount > withdrawable_balance:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Amount exceeds the withdrawable balance of INR {withdrawable_balance:.2f}",
        )

    balance_after = balance_before - data.amount
    transaction = CashTransaction(
        receipt_number=generate_receipt_number(db),
        account_id=account.id,
        branch_id=account.branch_id,
        staff_user_id=current_user.id,
        transaction_type="withdrawal",
        amount=data.amount,
        balance_before=balance_before,
        balance_after=balance_after,
        notes=data.notes.strip() if data.notes and data.notes.strip() else None,
    )
    account.balance = balance_after
    db.add(transaction)
    add_member_notification(
        db,
        recipient_id=account.member_id,
        notification_type="cash_withdrawal_processed",
        title="Cash withdrawal completed",
        message=(
            f"Cash withdrawal of INR {data.amount:.2f} processed from account "
            f"{account.account_number}. New balance: INR {balance_after:.2f}. "
            f"Receipt: {transaction.receipt_number}."
        ),
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Withdrawal could not be recorded due to a transaction conflict",
        ) from error

    db.refresh(transaction)
    row = transaction_query(db).filter(CashTransaction.id == transaction.id).first()
    return to_transaction_out(row)


@staff_router.get("/savings-accounts/lookup", response_model=CashierAccountLookupOut)
def lookup_cashier_savings_account(
    account_number: str = Query(..., pattern=r"^\d{16}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")

    row = (
        db.query(SavingsAccount, User, SavingsScheme, Branch)
        .join(User, SavingsAccount.member_id == User.id)
        .join(SavingsScheme, SavingsAccount.savings_scheme_id == SavingsScheme.id)
        .join(Branch, SavingsAccount.branch_id == Branch.id)
        .filter(
            SavingsAccount.account_number == account_number,
            SavingsAccount.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found in your branch")

    account, member, scheme, branch = row
    withdrawable_balance = (
        max(account.balance - scheme.lock_in_amount, Decimal("0.00"))
        if account.status == "active"
        else Decimal("0.00")
    )
    return CashierAccountLookupOut(
        account_id=account.id,
        account_number=account.account_number,
        member_code=member.user_code,
        member_name=member.full_name,
        scheme_name=scheme.scheme_name,
        status=account.status,
        balance=account.balance,
        lock_in_amount=scheme.lock_in_amount,
        withdrawable_balance=withdrawable_balance,
        branch_name=branch.name,
        can_accept_deposit=account.status in {"active", "awaiting_initial_deposit"},
        can_withdraw=account.status == "active" and withdrawable_balance > 0,
    )


@staff_router.get("/cash-transactions", response_model=List[CashTransactionOut])
def list_my_cash_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    account_number: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    return list_transactions(
        db,
        branch_id=current_user.branch_id,
        staff_user_id=current_user.id,
        account_number=account_number,
        skip=skip,
        limit=limit,
    )


@branch_admin_router.get("", response_model=List[CashTransactionOut])
def list_branch_cash_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    staff_user_id: int | None = Query(default=None, gt=0),
    account_number: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    if staff_user_id is not None:
        staff_exists = db.query(Staff.id).join(User, Staff.user_id == User.id).filter(
            Staff.user_id == staff_user_id,
            User.branch_id == current_user.branch_id,
            User.role == "staff",
            User.is_deleted == False,
        ).first()
        if not staff_exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found in your branch")
    return list_transactions(
        db,
        branch_id=current_user.branch_id,
        staff_user_id=staff_user_id,
        account_number=account_number,
        skip=skip,
        limit=limit,
    )


@superadmin_router.get("", response_model=List[CashTransactionOut])
def list_superadmin_cash_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    branch_id: int | None = Query(default=None, gt=0),
    staff_user_id: int | None = Query(default=None, gt=0),
    account_number: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    if branch_id is not None:
        branch = db.query(Branch.id).filter(
            Branch.id == branch_id,
            Branch.is_deleted == False,
        ).first()
        if not branch:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    return list_transactions(
        db,
        branch_id=branch_id,
        staff_user_id=staff_user_id,
        account_number=account_number,
        skip=skip,
        limit=limit,
    )


@member_router.get("/{account_id}/transactions", response_model=List[CashTransactionOut])
def list_my_savings_account_transactions(
    account_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    account = db.query(SavingsAccount.id).filter(
        SavingsAccount.id == account_id,
        SavingsAccount.member_id == current_user.id,
    ).first()
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found")
    rows = (
        transaction_query(db)
        .filter(
            CashTransaction.account_id == account_id,
            SavingsAccount.member_id == current_user.id,
        )
        .order_by(CashTransaction.created_at.desc(), CashTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_transaction_out(row) for row in rows]
