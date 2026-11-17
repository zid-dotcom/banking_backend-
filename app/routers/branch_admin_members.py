from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_roles
from app.core.security_events import add_security_event
from app.core.uploads import read_member_file
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.user import User
from app.schemas.member_admin import (
    MemberActiveUpdate,
    MemberDetailOut,
    MemberListOut,
    MemberNomineeOut,
    MemberPasswordReset,
    MemberStatusUpdate,
)

router = APIRouter(prefix="/branch-admin/members", tags=["Branch Admin - Members"])

DOC_FIELDS = {
    "aadhaar_front": "aadhaar_front_path",
    "aadhaar_back": "aadhaar_back_path",
    "pan_image": "pan_image_path",
    "passbook_image": "passbook_image_path",
}


def get_member_or_404(db: Session, member_id: int, branch_id: int) -> tuple[Member, User]:
    row = (
        db.query(Member, User)
        .join(User, Member.user_id == User.id)
        .filter(
            Member.id == member_id,
            User.role == "member",
            User.branch_id == branch_id,   # own branch only
            User.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return row


def to_nominee_out(nominee: Nominee | None) -> MemberNomineeOut:
    if nominee is None:
        return MemberNomineeOut(status="not_submitted")
    base = f"/branch-admin/nominees/{nominee.id}/documents"
    return MemberNomineeOut(
        status=nominee.status,
        nominee_name=nominee.nominee_name,
        relationship_type=nominee.relationship_type,
        date_of_birth=nominee.date_of_birth,
        aadhaar_front_url=f"{base}/aadhaar_front",
        aadhaar_back_url=f"{base}/aadhaar_back",
        rejection_reason=nominee.rejection_reason,
        submitted_at=nominee.submitted_at,
        reviewed_at=nominee.reviewed_at,
    )


def to_list_out(m: Member, u: User, nominee: Nominee | None = None) -> MemberListOut:
    return MemberListOut(
        id=m.id, member_code=u.user_code, full_name=u.full_name, email=u.email,
        mobile=u.contact_number, city=m.city, status=m.status,
        is_active=u.is_active, created_at=u.created_at,
        nominee=to_nominee_out(nominee),
    )


def to_detail_out(m: Member, u: User, nominee: Nominee | None = None) -> MemberDetailOut:
    base = f"/branch-admin/members/{m.id}/documents"
    return MemberDetailOut(
        id=m.id, member_code=u.user_code, full_name=u.full_name, email=u.email,
        mobile=u.contact_number, branch_id=u.branch_id,
        date_of_birth=m.date_of_birth, gender=m.gender, country=m.country,
        state=m.state, district=m.district, city=m.city, street=m.street,
        building_no=m.building_no, zip_code=m.zip_code,
        aadhaar_number=m.aadhaar_number, pan_number=m.pan_number,
        bank_holder_name=m.bank_holder_name, bank_account_number=m.bank_account_number,
        ifsc_code=m.ifsc_code,
        aadhaar_front_url=f"{base}/aadhaar_front", aadhaar_back_url=f"{base}/aadhaar_back",
        pan_image_url=f"{base}/pan_image", passbook_image_url=f"{base}/passbook_image",
        status=m.status, rejection_reason=m.rejection_reason, reviewed_at=m.reviewed_at,
        is_active=u.is_active, created_at=u.created_at,
        nominee=to_nominee_out(nominee),
    )


@router.get("", response_model=List[MemberListOut])
def list_members(
    skip: int = 0,
    limit: int = 20,
    member_status: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        db.query(Member, User, Nominee)
        .join(User, Member.user_id == User.id)
        .outerjoin(Nominee, Nominee.member_id == Member.id)
        .filter(
            User.role == "member",
            User.branch_id == current_user.branch_id,
            User.is_deleted == False,
        )
    )
    if member_status:
        query = query.filter(Member.status == member_status)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            User.full_name.ilike(like), User.email.ilike(like),
            User.user_code.ilike(like), User.contact_number.ilike(like),
        ))
    rows = query.order_by(Member.id.desc()).offset(skip).limit(limit).all()
    return [to_list_out(m, u, nominee) for m, u, nominee in rows]


@router.get("/{member_id}", response_model=MemberDetailOut)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    m, u = get_member_or_404(db, member_id, current_user.branch_id)
    nominee = db.query(Nominee).filter(Nominee.member_id == m.id).first()
    return to_detail_out(m, u, nominee)


@router.get("/{member_id}/documents/{doc_name}")
def get_member_document(
    member_id: int,
    doc_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if doc_name not in DOC_FIELDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    m, _ = get_member_or_404(db, member_id, current_user.branch_id)
    try:
        content, media_type = read_member_file(getattr(m, DOC_FIELDS[doc_name]))
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on server")
    return Response(content, media_type=media_type, headers={"Cache-Control": "no-store"})

@router.patch("/{member_id}/status", response_model=MemberDetailOut)
def review_member(
    member_id: int,
    data: MemberStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    m, u = get_member_or_404(db, member_id, current_user.branch_id)

    if m.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Member already {m.status}")

    m.status = data.status
    m.rejection_reason = data.rejection_reason
    m.reviewed_by = current_user.id
    m.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    nominee = db.query(Nominee).filter(Nominee.member_id == m.id).first()
    return to_detail_out(m, u, nominee)


@router.patch("/{member_id}/active", response_model=MemberListOut)
def change_member_active(
    member_id: int,
    data: MemberActiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    m, u = get_member_or_404(db, member_id, current_user.branch_id)

    if u.is_active == data.is_active:
        state = "active" if data.is_active else "inactive"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Member already {state}")

    u.is_active = data.is_active
    db.commit()
    db.refresh(u)
    nominee = db.query(Nominee).filter(Nominee.member_id == m.id).first()
    return to_list_out(m, u, nominee)


@router.patch("/{member_id}/reset-password")
def reset_member_password(
    member_id: int,
    request: Request,
    data: MemberPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    _, user = get_member_or_404(db, member_id, current_user.branch_id)
    user.hashed_password = hash_password(data.new_password)
    user.failed_attempts = 0
    user.locked_until = None
    add_security_event(
        db, event_type="password_reset", succeeded=True, user=user,
        actor=current_user, details="Password reset by branch admin",
        request=request,
    )
    db.commit()
    return {"message": "Member password reset", "member_code": user.user_code}


@router.patch("/{member_id}/unlock")
def unlock_member(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    _, user = get_member_or_404(db, member_id, current_user.branch_id)
    user.failed_attempts = 0
    user.locked_until = None
    add_security_event(
        db, event_type="account_unlocked", succeeded=True, user=user,
        actor=current_user, details="Account unlocked by branch admin",
        request=request,
    )
    db.commit()
    return {"message": "Member unlocked", "member_code": user.user_code}