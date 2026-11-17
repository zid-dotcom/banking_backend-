import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.notifications import add_member_notification
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.savings_account import SavingsAccount, SavingsAccountOpeningRequest
from app.models.savings_scheme import SavingsScheme
from app.models.user import User
from app.schemas.savings_account import (
    BranchAdminSavingsAccountOpeningRequestOut,
    SavingsAccountDetailsOut,
    SavingsAccountOpeningDecision,
)

router = APIRouter(
    prefix="/branch-admin/savings-account-requests",
    tags=["Branch Admin - Savings Accounts"],
)


def generate_account_number(db: Session) -> str:
    for _ in range(20):
        account_number = str(secrets.randbelow(9_000_000_000_000_000) + 1_000_000_000_000_000)
        exists = db.query(SavingsAccount.id).filter(
            SavingsAccount.account_number == account_number
        ).first()
        if not exists:
            return account_number
    raise HTTPException(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Could not generate a unique savings account number",
    )


def to_account_out(account: SavingsAccount | None) -> SavingsAccountDetailsOut | None:
    if account is None:
        return None
    return SavingsAccountDetailsOut(
        id=account.id,
        account_number=account.account_number,
        savings_scheme_id=account.savings_scheme_id,
        scheme_name=account.scheme.scheme_name,
        scheme_code=account.scheme.scheme_code,
        branch_id=account.branch_id,
        branch_name=account.branch.name,
        branch_code=account.branch.branch_code,
        ifsc_code=account.branch.ifsc_code,
        balance=account.balance,
        status=account.status,
        opened_at=account.opened_at,
    )


def request_query(db: Session):
    return (
        db.query(SavingsAccountOpeningRequest, User, Member, SavingsScheme, Nominee)
        .join(User, SavingsAccountOpeningRequest.member_id == User.id)
        .join(Member, Member.user_id == User.id)
        .join(SavingsScheme, SavingsAccountOpeningRequest.savings_scheme_id == SavingsScheme.id)
        .outerjoin(Nominee, Nominee.member_id == Member.id)
    )


def to_request_out(
    opening_request: SavingsAccountOpeningRequest,
    user: User,
    member: Member,
    scheme: SavingsScheme,
    nominee: Nominee | None,
) -> BranchAdminSavingsAccountOpeningRequestOut:
    return BranchAdminSavingsAccountOpeningRequestOut(
        id=opening_request.id,
        savings_scheme_id=scheme.id,
        scheme_name=scheme.scheme_name,
        scheme_code=scheme.scheme_code,
        status=opening_request.status,
        rejection_reason=opening_request.rejection_reason,
        created_at=opening_request.created_at,
        reviewed_at=opening_request.reviewed_at,
        account=to_account_out(opening_request.account),
        member_id=user.id,
        member_code=user.user_code,
        member_name=user.full_name,
        member_email=user.email,
        member_mobile=user.contact_number,
        member_kyc_status=member.status,
        nominee_status=nominee.status if nominee else "not_submitted",
    )


def get_branch_request_or_404(
    db: Session,
    request_id: int,
    branch_id: int,
) -> tuple[SavingsAccountOpeningRequest, User, Member, SavingsScheme, Nominee | None]:
    row = (
        request_query(db)
        .options(
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.branch),
        )
        .filter(
            SavingsAccountOpeningRequest.id == request_id,
            SavingsAccountOpeningRequest.branch_id == branch_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account request not found")
    return row


@router.get("", response_model=List[BranchAdminSavingsAccountOpeningRequestOut])
def list_branch_savings_account_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    request_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|approved|rejected)$",
    ),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        request_query(db)
        .options(
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.branch),
        )
        .filter(SavingsAccountOpeningRequest.branch_id == current_user.branch_id)
    )
    if request_status is not None:
        query = query.filter(SavingsAccountOpeningRequest.status == request_status)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(like),
                User.user_code.ilike(like),
                User.email.ilike(like),
                SavingsScheme.scheme_name.ilike(like),
                SavingsScheme.scheme_code.ilike(like),
            )
        )
    rows = (
        query.order_by(
            SavingsAccountOpeningRequest.created_at.desc(),
            SavingsAccountOpeningRequest.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_request_out(*row) for row in rows]


@router.get("/{request_id}", response_model=BranchAdminSavingsAccountOpeningRequestOut)
def get_branch_savings_account_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    return to_request_out(*get_branch_request_or_404(db, request_id, current_user.branch_id))


@router.patch("/{request_id}/decision", response_model=BranchAdminSavingsAccountOpeningRequestOut)
def decide_savings_account_request(
    request_id: int,
    data: SavingsAccountOpeningDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    locked_request = db.query(SavingsAccountOpeningRequest).filter(
        SavingsAccountOpeningRequest.id == request_id,
        SavingsAccountOpeningRequest.branch_id == current_user.branch_id,
    ).with_for_update().first()
    if not locked_request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account request not found")

    opening_request, user, member, scheme, nominee = get_branch_request_or_404(
        db, request_id, current_user.branch_id
    )
    if opening_request.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Savings account request already {opening_request.status}",
        )

    now = datetime.now(timezone.utc)
    account = None
    if data.status == "approved":
        if member.status != "approved":
            raise HTTPException(status.HTTP_409_CONFLICT, "Member KYC is not approved")
        if nominee is None or nominee.status != "approved":
            raise HTTPException(status.HTTP_409_CONFLICT, "Nominee details are not approved")
        if not scheme.is_active or scheme.is_deleted:
            raise HTTPException(status.HTTP_409_CONFLICT, "Savings scheme is no longer available")

        branch = db.query(Branch).filter(
            Branch.id == opening_request.branch_id,
            Branch.is_active == True,
            Branch.is_deleted == False,
        ).first()
        if not branch:
            raise HTTPException(status.HTTP_409_CONFLICT, "Branch is unavailable")

        account_status = (
            "awaiting_initial_deposit"
            if scheme.min_opening_balance > 0
            else "active"
        )
        account = SavingsAccount(
            account_number=generate_account_number(db),
            opening_request_id=opening_request.id,
            member_id=opening_request.member_id,
            branch_id=opening_request.branch_id,
            savings_scheme_id=scheme.id,
            balance=0,
            status=account_status,
            opened_at=now,
        )
        db.add(account)
        opening_request.status = "approved"
        opening_request.rejection_reason = None
        notification_message = (
            f"Your savings account request for {scheme.scheme_name} was approved. "
            f"Account number: {account.account_number}."
        )
        if account_status == "awaiting_initial_deposit":
            notification_message += (
                f" Deposit at least {scheme.min_opening_balance:.2f} to activate the account."
            )
        notification_type = "savings_account_opening_approved"
        notification_title = "Savings account approved"
    else:
        opening_request.status = "rejected"
        opening_request.rejection_reason = data.rejection_reason
        notification_message = (
            f"Your savings account request for {scheme.scheme_name} was rejected: "
            f"{data.rejection_reason}"
        )
        notification_type = "savings_account_opening_rejected"
        notification_title = "Savings account request rejected"

    opening_request.reviewed_by = current_user.id
    opening_request.reviewed_at = now
    add_member_notification(
        db,
        recipient_id=opening_request.member_id,
        notification_type=notification_type,
        title=notification_title,
        message=notification_message,
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Could not create the savings account because its account number conflicted",
        ) from error

    db.refresh(opening_request)
    if account:
        db.refresh(account)
        opening_request.account = account
    row = get_branch_request_or_404(db, request_id, current_user.branch_id)
    return to_request_out(*row)
