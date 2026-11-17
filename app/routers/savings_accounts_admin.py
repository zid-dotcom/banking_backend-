from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.savings_account import SavingsAccount, SavingsAccountOpeningRequest
from app.models.savings_scheme import SavingsScheme
from app.models.user import User
from app.schemas.savings_account import SavingsAccountAdminOut

branch_admin_router = APIRouter(
    prefix="/branch-admin/savings-accounts",
    tags=["Branch Admin - Savings Accounts"],
)
superadmin_router = APIRouter(
    prefix="/superadmin/savings-accounts",
    tags=["Superadmin - Savings Accounts"],
)


def account_query(db: Session):
    reviewer = aliased(User)
    query = (
        db.query(
            SavingsAccount,
            User,
            Member,
            SavingsScheme,
            Branch,
            Nominee,
            SavingsAccountOpeningRequest,
            reviewer,
        )
        .join(User, SavingsAccount.member_id == User.id)
        .join(Member, Member.user_id == User.id)
        .join(SavingsScheme, SavingsAccount.savings_scheme_id == SavingsScheme.id)
        .join(Branch, SavingsAccount.branch_id == Branch.id)
        .outerjoin(Nominee, Nominee.member_id == Member.id)
        .join(
            SavingsAccountOpeningRequest,
            SavingsAccount.opening_request_id == SavingsAccountOpeningRequest.id,
        )
        .outerjoin(reviewer, SavingsAccountOpeningRequest.reviewed_by == reviewer.id)
    )
    return query


def to_account_admin_out(row) -> SavingsAccountAdminOut:
    account, user, member, scheme, branch, nominee, opening_request, reviewer = row
    return SavingsAccountAdminOut(
        id=account.id,
        account_number=account.account_number,
        savings_scheme_id=scheme.id,
        scheme_name=scheme.scheme_name,
        scheme_code=scheme.scheme_code,
        branch_id=branch.id,
        branch_name=branch.name,
        branch_code=branch.branch_code,
        ifsc_code=branch.ifsc_code,
        balance=account.balance,
        status=account.status,
        opened_at=account.opened_at,
        member_id=user.id,
        member_code=user.user_code,
        member_name=user.full_name,
        member_email=user.email,
        member_mobile=user.contact_number,
        member_kyc_status=member.status,
        nominee_status=nominee.status if nominee else "not_submitted",
        branch_city=branch.city,
        branch_state=branch.state,
        branch_address=branch.address,
        branch_contact_number=branch.contact_number,
        opening_request_id=opening_request.id,
        opening_request_status=opening_request.status,
        request_created_at=opening_request.created_at,
        reviewed_at=opening_request.reviewed_at,
        reviewed_by_name=reviewer.full_name if reviewer else None,
    )


def list_accounts(
    db: Session,
    *,
    branch_id: int | None,
    account_status: str | None,
    search: str | None,
    skip: int,
    limit: int,
) -> list[SavingsAccountAdminOut]:
    query = account_query(db)
    if branch_id is not None:
        query = query.filter(SavingsAccount.branch_id == branch_id)
    if account_status is not None:
        query = query.filter(SavingsAccount.status == account_status)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SavingsAccount.account_number.ilike(like),
                User.full_name.ilike(like),
                User.user_code.ilike(like),
                User.email.ilike(like),
                SavingsScheme.scheme_name.ilike(like),
                SavingsScheme.scheme_code.ilike(like),
            )
        )
    rows = (
        query.order_by(SavingsAccount.opened_at.desc(), SavingsAccount.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_account_admin_out(row) for row in rows]


def get_account(
    db: Session,
    account_id: int,
    *,
    branch_id: int | None = None,
) -> SavingsAccountAdminOut:
    query = account_query(db).filter(SavingsAccount.id == account_id)
    if branch_id is not None:
        query = query.filter(SavingsAccount.branch_id == branch_id)
    row = query.first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Savings account not found")
    return to_account_admin_out(row)


@branch_admin_router.get("", response_model=List[SavingsAccountAdminOut])
def list_branch_savings_accounts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    account_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(active|awaiting_initial_deposit|closed)$",
    ),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if current_user.branch_id is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your account is not assigned to a branch",
        )
    return list_accounts(
        db,
        branch_id=current_user.branch_id,
        account_status=account_status,
        search=search,
        skip=skip,
        limit=limit,
    )


@branch_admin_router.get("/{account_id}", response_model=SavingsAccountAdminOut)
def get_branch_savings_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if current_user.branch_id is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your account is not assigned to a branch",
        )
    return get_account(db, account_id, branch_id=current_user.branch_id)


@superadmin_router.get("", response_model=List[SavingsAccountAdminOut])
def list_superadmin_savings_accounts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    branch_id: int | None = Query(default=None, gt=0),
    account_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(active|awaiting_initial_deposit|closed)$",
    ),
    search: str | None = None,
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
    return list_accounts(
        db,
        branch_id=branch_id,
        account_status=account_status,
        search=search,
        skip=skip,
        limit=limit,
    )


@superadmin_router.get("/{account_id}", response_model=SavingsAccountAdminOut)
def get_superadmin_savings_account(
    account_id: int,
    branch_id: int | None = Query(default=None, gt=0),
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
    return get_account(db, account_id, branch_id=branch_id)
