from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.cash_reconciliation import CashReconciliation
from app.models.cash_transaction import CashTransaction
from app.models.staff import Staff
from app.models.staff_role import StaffRole
from app.models.user import User
from app.routers.cash_transactions import get_cashier_role
from app.schemas.cash_reconciliation import (
    BranchDailyCashReportOut,
    CashDayClosingIn,
    CashDayOpeningIn,
    CashReconciliationDetailsOut,
    CashReconciliationOut,
    CashReconciliationReviewIn,
    CashReconciliationTransactionOut,
)

cashier_router = APIRouter(prefix="/staff/cash-reconciliation", tags=["Staff - Cash Reconciliation"])
accountant_router = APIRouter(
    prefix="/staff/accountant/cash-reconciliations",
    tags=["Accountant - Cash Reconciliation"],
)
branch_admin_router = APIRouter(
    prefix="/branch-admin/cash-reconciliations",
    tags=["Branch Admin - Cash Reconciliation"],
)


def require_accountant(db: Session, user_id: int) -> StaffRole:
    role = (
        db.query(StaffRole)
        .join(Staff, Staff.staff_role_id == StaffRole.id)
        .filter(
            Staff.user_id == user_id,
            StaffRole.is_deleted == False,
        )
        .first()
    )
    if not role or role.name.strip().casefold() != "accountant":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only Accountant staff can review cash reconciliations",
        )
    return role


def get_branch_id(user: User) -> int:
    if user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    return user.branch_id


def to_reconciliation_out(
    db: Session,
    reconciliation: CashReconciliation,
) -> CashReconciliationOut:
    cashier = db.query(User).filter(User.id == reconciliation.cashier_user_id).first()
    accountant = None
    if reconciliation.accountant_user_id is not None:
        accountant = db.query(User).filter(User.id == reconciliation.accountant_user_id).first()
    if not cashier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cashier account not found")
    return CashReconciliationOut(
        id=reconciliation.id,
        business_date=reconciliation.business_date,
        branch_id=reconciliation.branch_id,
        cashier_user_id=cashier.id,
        cashier_code=cashier.user_code,
        cashier_name=cashier.full_name,
        opening_cash=reconciliation.opening_cash,
        closing_cash=reconciliation.closing_cash,
        deposit_total=reconciliation.deposit_total,
        withdrawal_total=reconciliation.withdrawal_total,
        expected_closing_cash=reconciliation.expected_closing_cash,
        difference=reconciliation.difference,
        status=reconciliation.status,
        accountant_user_id=reconciliation.accountant_user_id,
        accountant_name=accountant.full_name if accountant else None,
        accountant_explanation=reconciliation.accountant_explanation,
        opened_at=reconciliation.opened_at,
        closed_at=reconciliation.closed_at,
        reviewed_at=reconciliation.reviewed_at,
    )


def get_report_or_404(
    db: Session,
    report_id: int,
    branch_id: int,
) -> CashReconciliation:
    report = db.query(CashReconciliation).filter(
        CashReconciliation.id == report_id,
        CashReconciliation.branch_id == branch_id,
    ).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cash reconciliation not found")
    return report


def get_report_transactions(
    db: Session,
    report: CashReconciliation,
):
    end_time = report.closed_at or datetime.now(timezone.utc)
    rows = (
        db.query(CashTransaction)
        .filter(
            CashTransaction.branch_id == report.branch_id,
            CashTransaction.staff_user_id == report.cashier_user_id,
            CashTransaction.created_at >= report.opened_at,
            CashTransaction.created_at <= end_time,
        )
        .order_by(CashTransaction.created_at, CashTransaction.id)
        .all()
    )
    return [
        CashReconciliationTransactionOut(
            id=transaction.id,
            receipt_number=transaction.receipt_number,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            notes=transaction.notes,
            created_at=transaction.created_at,
        )
        for transaction in rows
    ]


@cashier_router.post(
    "/open",
    response_model=CashReconciliationOut,
    status_code=status.HTTP_201_CREATED,
)
def open_cash_day(
    data: CashDayOpeningIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    branch_id = get_branch_id(current_user)

    already_open = db.query(CashReconciliation.id).filter(
        CashReconciliation.cashier_user_id == current_user.id,
        CashReconciliation.status == "open",
    ).first()
    if already_open:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an open cash day")
    existing_date = db.query(CashReconciliation.id).filter(
        CashReconciliation.cashier_user_id == current_user.id,
        CashReconciliation.business_date == data.business_date,
    ).first()
    if existing_date:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A cash reconciliation already exists for this business date",
        )

    report = CashReconciliation(
        branch_id=branch_id,
        cashier_user_id=current_user.id,
        business_date=data.business_date,
        opening_cash=data.opening_cash,
        status="open",
        opened_at=datetime.now(timezone.utc),
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A cash day is already open or recorded for this date",
        ) from error
    db.refresh(report)
    return to_reconciliation_out(db, report)


@cashier_router.post("/close", response_model=CashReconciliationOut)
def close_cash_day(
    data: CashDayClosingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    branch_id = get_branch_id(current_user)
    report = (
        db.query(CashReconciliation)
        .filter(
            CashReconciliation.cashier_user_id == current_user.id,
            CashReconciliation.branch_id == branch_id,
            CashReconciliation.status == "open",
        )
        .with_for_update()
        .first()
    )
    if not report:
        raise HTTPException(status.HTTP_409_CONFLICT, "You do not have an open cash day")

    closed_at = datetime.now(timezone.utc)
    transactions = db.query(CashTransaction).filter(
        CashTransaction.branch_id == branch_id,
        CashTransaction.staff_user_id == current_user.id,
        CashTransaction.created_at >= report.opened_at,
        CashTransaction.created_at <= closed_at,
    ).all()
    deposits = sum(
        (transaction.amount for transaction in transactions if transaction.transaction_type == "deposit"),
        Decimal("0.00"),
    )
    withdrawals = sum(
        (transaction.amount for transaction in transactions if transaction.transaction_type == "withdrawal"),
        Decimal("0.00"),
    )
    expected_closing_cash = report.opening_cash + deposits - withdrawals

    report.closing_cash = data.closing_cash
    report.deposit_total = deposits
    report.withdrawal_total = withdrawals
    report.expected_closing_cash = expected_closing_cash
    report.difference = data.closing_cash - expected_closing_cash
    report.closed_at = closed_at
    report.status = "submitted"
    db.commit()
    db.refresh(report)
    return to_reconciliation_out(db, report)


@cashier_router.get("", response_model=List[CashReconciliationOut])
def list_my_cash_days(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    business_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    get_cashier_role(db, current_user.id)
    query = db.query(CashReconciliation).filter(
        CashReconciliation.cashier_user_id == current_user.id,
        CashReconciliation.branch_id == get_branch_id(current_user),
    )
    if business_date is not None:
        query = query.filter(CashReconciliation.business_date == business_date)
    reports = query.order_by(
        CashReconciliation.business_date.desc(),
        CashReconciliation.id.desc(),
    ).offset(skip).limit(limit).all()
    return [to_reconciliation_out(db, report) for report in reports]


@accountant_router.get("", response_model=List[CashReconciliationOut])
def list_accountant_cash_days(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    business_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    report_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(open|submitted|reconciled|reported)$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    require_accountant(db, current_user.id)
    if (from_date is None) != (to_date is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Both from_date and to_date are required for a date range",
        )
    if business_date is not None and from_date is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Use business_date or a from_date/to_date range, not both",
        )
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "from_date must be on or before to_date",
        )

    query = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == get_branch_id(current_user),
    )
    if business_date is not None:
        query = query.filter(CashReconciliation.business_date == business_date)
    elif from_date is not None and to_date is not None:
        query = query.filter(
            CashReconciliation.business_date >= from_date,
            CashReconciliation.business_date <= to_date,
        )
    if report_status is not None:
        query = query.filter(CashReconciliation.status == report_status)
    reports = query.order_by(
        CashReconciliation.business_date.desc(),
        CashReconciliation.cashier_user_id,
    ).offset(skip).limit(limit).all()
    return [to_reconciliation_out(db, report) for report in reports]


@accountant_router.get("/{report_id}", response_model=CashReconciliationDetailsOut)
def get_accountant_cash_day(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    require_accountant(db, current_user.id)
    report = get_report_or_404(db, report_id, get_branch_id(current_user))
    return CashReconciliationDetailsOut(
        **to_reconciliation_out(db, report).model_dump(),
        transactions=get_report_transactions(db, report),
    )


@accountant_router.patch("/{report_id}/review", response_model=CashReconciliationOut)
def review_cash_day(
    report_id: int,
    data: CashReconciliationReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("staff")),
):
    require_accountant(db, current_user.id)
    report = (
        db.query(CashReconciliation)
        .filter(
            CashReconciliation.id == report_id,
            CashReconciliation.branch_id == get_branch_id(current_user),
        )
        .with_for_update()
        .first()
    )
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cash reconciliation not found")
    if report.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only submitted cash days can be reviewed")

    explanation = data.explanation.strip() if data.explanation else None
    if report.difference != Decimal("0.00") and not explanation:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "An explanation is required when the counted cash differs from the expected cash",
        )

    report.accountant_user_id = current_user.id
    report.accountant_explanation = explanation
    report.reviewed_at = datetime.now(timezone.utc)
    report.status = "reported" if report.difference != Decimal("0.00") else "reconciled"
    db.commit()
    db.refresh(report)
    return to_reconciliation_out(db, report)


@branch_admin_router.get("/daily-report", response_model=BranchDailyCashReportOut)
def get_branch_daily_cash_report(
    business_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    branch_id = get_branch_id(current_user)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")

    reports = db.query(CashReconciliation).filter(
        CashReconciliation.branch_id == branch_id,
        CashReconciliation.business_date == business_date,
    ).order_by(CashReconciliation.cashier_user_id).all()
    return build_branch_daily_cash_report(db, branch, business_date, reports)


def build_branch_daily_cash_report(
    db: Session,
    branch: Branch,
    business_date: date,
    reports: list[CashReconciliation],
) -> BranchDailyCashReportOut:
    closed_reports = [report for report in reports if report.closing_cash is not None]
    zero = Decimal("0.00")
    return BranchDailyCashReportOut(
        business_date=business_date,
        branch_id=branch.id,
        branch_name=branch.name,
        cashier_count=len(reports),
        open_cashier_count=sum(report.status == "open" for report in reports),
        pending_accountant_review_count=sum(report.status == "submitted" for report in reports),
        total_opening_cash=sum((report.opening_cash for report in closed_reports), zero),
        total_deposits=sum((report.deposit_total for report in closed_reports), zero),
        total_withdrawals=sum((report.withdrawal_total for report in closed_reports), zero),
        total_expected_closing_cash=sum(
            (report.expected_closing_cash or zero for report in closed_reports),
            zero,
        ),
        total_counted_closing_cash=sum(
            (report.closing_cash or zero for report in closed_reports),
            zero,
        ),
        total_difference=sum((report.difference or zero for report in closed_reports), zero),
        cashier_reports=[to_reconciliation_out(db, report) for report in reports],
    )


@branch_admin_router.get(
    "/range-report",
    response_model=List[BranchDailyCashReportOut],
)
def get_branch_cash_reports_by_date_range(
    from_date: date,
    to_date: date,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=31, ge=1, le=366),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if from_date > to_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "from_date must be on or before to_date",
        )

    branch_id = get_branch_id(current_user)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")

    date_rows = (
        db.query(CashReconciliation.business_date)
        .filter(
            CashReconciliation.branch_id == branch_id,
            CashReconciliation.business_date >= from_date,
            CashReconciliation.business_date <= to_date,
        )
        .distinct()
        .order_by(CashReconciliation.business_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    business_dates = [row[0] for row in date_rows]
    if not business_dates:
        return []

    reports = (
        db.query(CashReconciliation)
        .filter(
            CashReconciliation.branch_id == branch_id,
            CashReconciliation.business_date.in_(business_dates),
        )
        .order_by(
            CashReconciliation.business_date.desc(),
            CashReconciliation.cashier_user_id,
        )
        .all()
    )
    reports_by_date: dict[date, list[CashReconciliation]] = {
        business_date: [] for business_date in business_dates
    }
    for report in reports:
        reports_by_date[report.business_date].append(report)
    return [
        build_branch_daily_cash_report(
            db,
            branch,
            business_date,
            reports_by_date[business_date],
        )
        for business_date in business_dates
    ]
