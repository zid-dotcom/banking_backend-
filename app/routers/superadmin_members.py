from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.core.uploads import read_member_file
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.user import User
from app.schemas.member_admin import (
    MemberDetailOut,
    MemberNomineeOut,
    SuperadminBranchMembersOut,
)

router = APIRouter(prefix="/superadmin/branches", tags=["Superadmin - Branch Members"])

MEMBER_DOCUMENT_FIELDS = {
    "aadhaar_front": "aadhaar_front_path",
    "aadhaar_back": "aadhaar_back_path",
    "pan_image": "pan_image_path",
    "passbook_image": "passbook_image_path",
}


def get_active_branch_or_404(db: Session, branch_id: int) -> Branch:
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.is_deleted == False,
        Branch.is_active == True,
    ).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active branch not found")
    return branch


def get_branch_member_or_404(
    db: Session, branch_id: int, member_id: int
) -> tuple[Member, User, Nominee | None]:
    row = (
        db.query(Member, User, Nominee)
        .join(User, Member.user_id == User.id)
        .outerjoin(Nominee, Nominee.member_id == Member.id)
        .filter(
            Member.id == member_id,
            User.branch_id == branch_id,
            User.role == "member",
            User.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return row


def to_nominee_out(
    nominee: Nominee | None, branch_id: int, member_id: int
) -> MemberNomineeOut:
    if nominee is None:
        return MemberNomineeOut(status="not_submitted")
    base = f"/superadmin/branches/{branch_id}/members/{member_id}/nominee/documents"
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


def to_superadmin_member_out(
    member: Member, user: User, nominee: Nominee | None
) -> MemberDetailOut:
    base = f"/superadmin/branches/{user.branch_id}/members/{member.id}/documents"
    return MemberDetailOut(
        id=member.id,
        member_code=user.user_code,
        full_name=user.full_name,
        email=user.email,
        mobile=user.contact_number,
        branch_id=user.branch_id,
        date_of_birth=member.date_of_birth,
        gender=member.gender,
        country=member.country,
        state=member.state,
        district=member.district,
        city=member.city,
        street=member.street,
        building_no=member.building_no,
        zip_code=member.zip_code,
        aadhaar_number=member.aadhaar_number,
        pan_number=member.pan_number,
        bank_holder_name=member.bank_holder_name,
        bank_account_number=member.bank_account_number,
        ifsc_code=member.ifsc_code,
        aadhaar_front_url=f"{base}/aadhaar_front",
        aadhaar_back_url=f"{base}/aadhaar_back",
        pan_image_url=f"{base}/pan_image",
        passbook_image_url=f"{base}/passbook_image",
        status=member.status,
        rejection_reason=member.rejection_reason,
        reviewed_at=member.reviewed_at,
        is_active=user.is_active,
        created_at=user.created_at,
        nominee=to_nominee_out(nominee, user.branch_id, member.id),
    )


@router.get("/{branch_id}/members", response_model=SuperadminBranchMembersOut)
def list_branch_members_for_superadmin(
    branch_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = get_active_branch_or_404(db, branch_id)
    rows = (
        db.query(Member, User, Nominee)
        .join(User, Member.user_id == User.id)
        .outerjoin(Nominee, Nominee.member_id == Member.id)
        .filter(
            User.branch_id == branch_id,
            User.role == "member",
            User.is_deleted == False,
        )
        .order_by(Member.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return SuperadminBranchMembersOut(
        branch=branch,
        members=[
            to_superadmin_member_out(member, user, nominee)
            for member, user, nominee in rows
        ],
    )


@router.get("/{branch_id}/members/{member_id}", response_model=MemberDetailOut)
def get_branch_member_for_superadmin(
    branch_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    get_active_branch_or_404(db, branch_id)
    member, user, nominee = get_branch_member_or_404(db, branch_id, member_id)
    return to_superadmin_member_out(member, user, nominee)


@router.get("/{branch_id}/members/{member_id}/documents/{doc_name}")
def get_branch_member_document_for_superadmin(
    branch_id: int,
    member_id: int,
    doc_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    get_active_branch_or_404(db, branch_id)
    if doc_name not in MEMBER_DOCUMENT_FIELDS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    member, _, _ = get_branch_member_or_404(db, branch_id, member_id)
    try:
        content, media_type = read_member_file(getattr(member, MEMBER_DOCUMENT_FIELDS[doc_name]))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on server")
    return Response(content, media_type=media_type)


@router.get("/{branch_id}/members/{member_id}/nominee/documents/{doc_name}")
def get_branch_member_nominee_document_for_superadmin(
    branch_id: int,
    member_id: int,
    doc_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    get_active_branch_or_404(db, branch_id)
    if doc_name not in {"aadhaar_front", "aadhaar_back"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    _, _, nominee = get_branch_member_or_404(db, branch_id, member_id)
    if nominee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nominee not submitted")

    path_field = f"{doc_name}_path"
    try:
        content, media_type = read_member_file(getattr(nominee, path_field))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on server")
    return Response(content, media_type=media_type, headers={"Cache-Control": "no-store"})
