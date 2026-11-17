from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_events import add_security_event
from app.core.security import create_access_token, require_roles, verify_login
from app.models.branch import Branch
from app.models.staff import Staff
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.branch_staff import StaffMeOut

router = APIRouter(prefix="/staff", tags=["Staff - Auth"])


@router.post("/login", response_model=TokenResponse)
def staff_login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.user_code == form.username.strip(),
        User.role == "staff",
        User.is_deleted == False,
    ).first()
    verify_login(
        db, user, form.password, "Incorrect staff code or password",
        request=request, expected_role="staff",
    )

    if not user.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Account is inactive", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is inactive")
    if not db.query(Staff.id).filter(Staff.user_id == user.id).first():
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Staff profile is missing", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff profile not found")
    branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
    if not branch or branch.is_deleted or not branch.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Branch is inactive or unavailable", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your branch is inactive")

    add_security_event(db, event_type="login_success", succeeded=True, user=user, request=request)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=StaffMeOut)
def staff_me(
    current_user: User = Depends(require_roles("staff")),
    db: Session = Depends(get_db),
):
    if current_user.branch_id is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your account is not assigned to a branch",
        )

    row = (
        db.query(Staff, StaffRole)
        .join(StaffRole, Staff.staff_role_id == StaffRole.id)
        .filter(
            Staff.user_id == current_user.id,
            StaffRole.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff profile or role not found")
    staff, staff_role = row

    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff branch not found")

    return StaffMeOut(
        staff_id=staff.id,
        user_id=current_user.id,
        staff_code=current_user.user_code,
        full_name=current_user.full_name,
        email=current_user.email,
        contact_number=current_user.contact_number,
        account_role=current_user.role,
        staff_role=staff_role,
        branch_id=branch.id,
        branch=branch,
        is_active=current_user.is_active,
        created_at=staff.created_at,
    )
