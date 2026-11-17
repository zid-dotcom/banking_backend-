from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee_change_request import NomineeChangeRequest
from app.models.user import User
from app.schemas.nominee_change_request import (
    BranchAdminNomineeChangeRequestOut,
    NomineeChangeRequestReview,
)

router = APIRouter(
    prefix="/branch-admin/nominee-change-requests",
    tags=["Branch Admin - Nominee Change Requests"],
)


def _to_out(change_request: NomineeChangeRequest, user: User, branch: Branch) -> dict:
    return {
        "id": change_request.id,
        "subject": change_request.subject,
        "message": change_request.message,
        "status": change_request.status,
        "rejection_reason": change_request.rejection_reason,
        "created_at": change_request.created_at,
        "reviewed_at": change_request.reviewed_at,
        "consumed_at": change_request.consumed_at,
        "member_id": change_request.member_id,
        "member_code": user.user_code,
        "member_name": user.full_name,
        "branch_id": user.branch_id,
        "branch_name": branch.name,
    }


def _get_request_or_404(db: Session, request_id: int, branch_id: int):
    row = (
        db.query(NomineeChangeRequest, User, Branch)
        .join(Member, NomineeChangeRequest.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .join(Branch, User.branch_id == Branch.id)
        .filter(
            NomineeChangeRequest.id == request_id,
            User.branch_id == branch_id,
            User.role == "member",
            User.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nominee change request not found")
    return row


@router.get("", response_model=List[BranchAdminNomineeChangeRequestOut])
def list_nominee_change_requests(
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
        db.query(NomineeChangeRequest, User, Branch)
        .join(Member, NomineeChangeRequest.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .join(Branch, User.branch_id == Branch.id)
        .filter(
            User.branch_id == current_user.branch_id,
            User.role == "member",
            User.is_deleted == False,
        )
    )
    if request_status is not None:
        query = query.filter(NomineeChangeRequest.status == request_status)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                NomineeChangeRequest.subject.ilike(like),
                NomineeChangeRequest.message.ilike(like),
                User.full_name.ilike(like),
                User.user_code.ilike(like),
            )
        )

    rows = (
        query.order_by(NomineeChangeRequest.created_at.desc(), NomineeChangeRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_out(change_request, user, branch) for change_request, user, branch in rows]


@router.get("/{request_id}", response_model=BranchAdminNomineeChangeRequestOut)
def get_nominee_change_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    change_request, user, branch = _get_request_or_404(db, request_id, current_user.branch_id)
    return _to_out(change_request, user, branch)


@router.patch("/{request_id}/status", response_model=BranchAdminNomineeChangeRequestOut)
def review_nominee_change_request(
    request_id: int,
    data: NomineeChangeRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    change_request, user, branch = _get_request_or_404(db, request_id, current_user.branch_id)
    if change_request.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Nominee change request is already {change_request.status}",
        )

    change_request.status = data.status
    change_request.rejection_reason = data.rejection_reason
    change_request.reviewed_by = current_user.id
    change_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(change_request)
    return _to_out(change_request, user, branch)
