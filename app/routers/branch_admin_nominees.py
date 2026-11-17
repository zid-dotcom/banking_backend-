from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.core.uploads import read_member_file
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.user import User
from app.schemas.nominee_admin import NomineeDetailOut, NomineeListOut, NomineeStatusUpdate

router = APIRouter(prefix="/branch-admin/nominees", tags=["Branch Admin - Nominees"])

DOC_FIELDS = {
    "aadhaar_front": "aadhaar_front_path",
    "aadhaar_back": "aadhaar_back_path",
}


def get_nominee_or_404(db: Session, nominee_id: int, branch_id: int) -> tuple[Nominee, User]:
    row = (
        db.query(Nominee, User)
        .join(Member, Nominee.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .filter(
            Nominee.id == nominee_id,
            User.role == "member",
            User.branch_id == branch_id,
            User.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nominee not found")
    return row


def to_list_out(nominee: Nominee, user: User) -> NomineeListOut:
    return NomineeListOut(
        id=nominee.id,
        member_code=user.user_code,
        member_name=user.full_name,
        nominee_name=nominee.nominee_name,
        relationship_type=nominee.relationship_type,
        status=nominee.status,
        submitted_at=nominee.submitted_at,
    )


def to_detail_out(nominee: Nominee, user: User) -> NomineeDetailOut:
    base = f"/branch-admin/nominees/{nominee.id}/documents"
    return NomineeDetailOut(
        id=nominee.id,
        member_code=user.user_code,
        member_name=user.full_name,
        nominee_name=nominee.nominee_name,
        relationship_type=nominee.relationship_type,
        date_of_birth=nominee.date_of_birth,
        aadhaar_front_url=f"{base}/aadhaar_front",
        aadhaar_back_url=f"{base}/aadhaar_back",
        status=nominee.status,
        rejection_reason=nominee.rejection_reason,
        submitted_at=nominee.submitted_at,
        reviewed_at=nominee.reviewed_at,
    )


@router.get("", response_model=List[NomineeListOut])
def list_nominees(
    skip: int = 0,
    limit: int = 20,
    nominee_status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        db.query(Nominee, User)
        .join(Member, Nominee.member_id == Member.id)
        .join(User, Member.user_id == User.id)
        .filter(
            User.role == "member",
            User.branch_id == current_user.branch_id,
            User.is_deleted == False,
        )
    )
    if nominee_status:
        query = query.filter(Nominee.status == nominee_status)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            Nominee.nominee_name.ilike(like),
            User.full_name.ilike(like),
            User.user_code.ilike(like),
        ))
    rows = query.order_by(Nominee.id.desc()).offset(skip).limit(limit).all()
    return [to_list_out(nominee, user) for nominee, user in rows]


@router.get("/{nominee_id}", response_model=NomineeDetailOut)
def get_nominee(
    nominee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    nominee, user = get_nominee_or_404(db, nominee_id, current_user.branch_id)
    return to_detail_out(nominee, user)


@router.get("/{nominee_id}/documents/{doc_name}")
def get_nominee_document(
    nominee_id: int,
    doc_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if doc_name not in DOC_FIELDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    nominee, _ = get_nominee_or_404(db, nominee_id, current_user.branch_id)
    try:
        content, media_type = read_member_file(getattr(nominee, DOC_FIELDS[doc_name]))
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on server")
    return Response(content, media_type=media_type, headers={"Cache-Control": "no-store"})


@router.patch("/{nominee_id}/status", response_model=NomineeDetailOut)
def review_nominee(
    nominee_id: int,
    data: NomineeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    nominee, user = get_nominee_or_404(db, nominee_id, current_user.branch_id)
    if nominee.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Nominee already {nominee.status}")

    nominee.status = data.status
    nominee.rejection_reason = data.rejection_reason
    nominee.reviewed_by = current_user.id
    nominee.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(nominee)
    return to_detail_out(nominee, user)
