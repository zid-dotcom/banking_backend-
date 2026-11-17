from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_events import add_security_event
from app.core.security import create_access_token, require_roles, verify_login
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.member import (
    MemberFullProfileOut,
    MemberMeOut,
    MemberNomineeProfileOut,
    MemberProfileOut,
)

router = APIRouter(prefix="/member", tags=["Member - Auth"])


def mask_tail(value: str, show: int = 4) -> str:
    return "X" * max(len(value) - show, 0) + value[-show:]


@router.post("/login", response_model=TokenResponse)
def member_login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # "username" field = member code
    user = db.query(User).filter(
        User.user_code == form.username.strip(),
        User.role == "member",
        User.is_deleted == False,
    ).first()

    verify_login(
        db, user, form.password, "Incorrect member code or password",
        request=request, expected_role="member",
    )

    if not user.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Account is disabled", request=request,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is disabled. Contact your branch")

    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Member profile is missing", request=request,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Member profile not found. Contact your branch")
    if member.status == "pending":
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Member registration is pending approval", request=request,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your registration is pending approval")
    if member.status == "rejected":
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Member registration was rejected", request=request,
        )
        db.commit()
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Your registration was rejected: {member.rejection_reason}. Please use re-apply to submit again.",
        )

    branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
    if not branch or branch.is_deleted or not branch.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Branch is inactive or unavailable", request=request,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your branch is inactive. Contact your branch")

    add_security_event(db, event_type="login_success", succeeded=True, user=user, request=request)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=MemberMeOut)
def member_me(
    current_user: User = Depends(require_roles("member")),
    db: Session = Depends(get_db),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")
    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member branch not found")

    return MemberMeOut(
        member_code=current_user.user_code,
        full_name=current_user.full_name,
        email=current_user.email,
        mobile=current_user.contact_number,
        branch_id=current_user.branch_id,
        branch=branch,
        status=member.status,
    )


@router.get("/profile", response_model=MemberProfileOut)
def member_profile(
    current_user: User = Depends(require_roles("member")),
    db: Session = Depends(get_db),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")
    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member branch not found")

    return MemberProfileOut(
        member_code=current_user.user_code,
        full_name=current_user.full_name,
        email=current_user.email,
        mobile=current_user.contact_number,
        branch_id=current_user.branch_id,
        branch=branch,
        date_of_birth=member.date_of_birth,
        gender=member.gender,
        country=member.country,
        state=member.state,
        district=member.district,
        city=member.city,
        street=member.street,
        building_no=member.building_no,
        zip_code=member.zip_code,
        aadhaar_masked=mask_tail(member.aadhaar_number),
        pan_masked=mask_tail(member.pan_number),
        bank_holder_name=member.bank_holder_name,
        bank_account_masked=mask_tail(member.bank_account_number),
        ifsc_code=member.ifsc_code,
        status=member.status,
    )


@router.get("/profile/full", response_model=MemberFullProfileOut)
def member_full_profile(
    current_user: User = Depends(require_roles("member")),
    db: Session = Depends(get_db),
):
    profile = member_profile(current_user, db)
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")

    nominee = db.query(Nominee).filter(Nominee.member_id == member.id).first()
    nominee_profile = MemberNomineeProfileOut(
        status=nominee.status if nominee else "not_submitted",
        nominee_name=nominee.nominee_name if nominee else None,
        relationship_type=nominee.relationship_type if nominee else None,
        date_of_birth=nominee.date_of_birth if nominee else None,
        rejection_reason=nominee.rejection_reason if nominee else None,
        submitted_at=nominee.submitted_at if nominee else None,
        reviewed_at=nominee.reviewed_at if nominee else None,
    )

    return MemberFullProfileOut(
        **profile.model_dump(),
        kyc_status=member.status,
        kyc_rejection_reason=member.rejection_reason,
        kyc_reviewed_at=member.reviewed_at,
        member_created_at=member.created_at,
        nominee=nominee_profile,
    )