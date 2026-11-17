from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.savings_account import SavingsAccount, SavingsAccountOpeningRequest
from app.models.savings_scheme import SavingsScheme
from app.models.user import User
from app.schemas.savings_account import (
    MemberSavingsAccountOpeningRequestOut,
    SavingsAccountDetailsOut,
    SavingsAccountOpeningRequestCreate,
)

router = APIRouter(prefix="/member", tags=["Member - Savings Accounts"])


def to_account_out(account: SavingsAccount) -> SavingsAccountDetailsOut:
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


def to_request_out(
    request: SavingsAccountOpeningRequest,
) -> MemberSavingsAccountOpeningRequestOut:
    return MemberSavingsAccountOpeningRequestOut(
        id=request.id,
        savings_scheme_id=request.savings_scheme_id,
        scheme_name=request.scheme.scheme_name,
        scheme_code=request.scheme.scheme_code,
        status=request.status,
        rejection_reason=request.rejection_reason,
        created_at=request.created_at,
        reviewed_at=request.reviewed_at,
        account=to_account_out(request.account) if request.account else None,
    )


@router.post(
    "/savings-account-requests",
    response_model=MemberSavingsAccountOpeningRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def create_savings_account_opening_request(
    data: SavingsAccountOpeningRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")
    if member.status != "approved":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Member KYC must be approved first")

    nominee = db.query(Nominee).filter(Nominee.member_id == member.id).first()
    if not nominee or nominee.status != "approved":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nominee details must be approved first")

    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")
    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_active == True,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your assigned branch is unavailable")

    scheme = db.query(SavingsScheme).filter(
        SavingsScheme.id == data.savings_scheme_id,
        SavingsScheme.is_active == True,
        SavingsScheme.is_deleted == False,
    ).first()
    if not scheme:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Available savings scheme not found")

    existing_request = db.query(SavingsAccountOpeningRequest).filter(
        SavingsAccountOpeningRequest.member_id == current_user.id,
        SavingsAccountOpeningRequest.savings_scheme_id == scheme.id,
        SavingsAccountOpeningRequest.status == "pending",
    ).first()
    if existing_request:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A request for this savings scheme is already pending",
        )

    opening_request = SavingsAccountOpeningRequest(
        member_id=current_user.id,
        branch_id=branch.id,
        savings_scheme_id=scheme.id,
        status="pending",
    )
    db.add(opening_request)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A request for this savings scheme is already pending",
        ) from error
    db.refresh(opening_request)
    return to_request_out(opening_request)


@router.get(
    "/savings-account-requests",
    response_model=List[MemberSavingsAccountOpeningRequestOut],
)
def list_my_savings_account_opening_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    request_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|approved|rejected)$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    query = (
        db.query(SavingsAccountOpeningRequest)
        .options(
            joinedload(SavingsAccountOpeningRequest.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.branch),
        )
        .filter(SavingsAccountOpeningRequest.member_id == current_user.id)
    )
    if request_status is not None:
        query = query.filter(SavingsAccountOpeningRequest.status == request_status)
    requests = query.order_by(
        SavingsAccountOpeningRequest.created_at.desc(),
        SavingsAccountOpeningRequest.id.desc(),
    ).offset(skip).limit(limit).all()
    return [to_request_out(request) for request in requests]


@router.get(
    "/savings-account-requests/{request_id}",
    response_model=MemberSavingsAccountOpeningRequestOut,
)
def get_my_savings_account_opening_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    opening_request = (
        db.query(SavingsAccountOpeningRequest)
        .options(
            joinedload(SavingsAccountOpeningRequest.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccountOpeningRequest.account).joinedload(SavingsAccount.branch),
        )
        .filter(
            SavingsAccountOpeningRequest.id == request_id,
            SavingsAccountOpeningRequest.member_id == current_user.id,
        )
        .first()
    )
    if not opening_request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account request not found")
    return to_request_out(opening_request)


@router.get("/savings-accounts", response_model=List[SavingsAccountDetailsOut])
def list_my_savings_accounts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    accounts = (
        db.query(SavingsAccount)
        .options(
            joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccount.branch),
        )
        .filter(SavingsAccount.member_id == current_user.id)
        .order_by(SavingsAccount.opened_at.desc(), SavingsAccount.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_account_out(account) for account in accounts]


@router.get("/savings-accounts/{account_id}", response_model=SavingsAccountDetailsOut)
def get_my_savings_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    account = (
        db.query(SavingsAccount)
        .options(
            joinedload(SavingsAccount.scheme),
            joinedload(SavingsAccount.branch),
        )
        .filter(
            SavingsAccount.id == account_id,
            SavingsAccount.member_id == current_user.id,
        )
        .first()
    )
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found")
    return to_account_out(account)
