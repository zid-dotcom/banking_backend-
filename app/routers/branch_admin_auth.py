from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_events import add_security_event
from app.core.security import create_access_token, require_roles, verify_login
from app.models.branch import Branch
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.branch_admin import BranchAdminMeOut

router = APIRouter(prefix="/branch-admin", tags=["Branch Admin - Auth"])


@router.post("/login", response_model=TokenResponse)
def branch_admin_login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # "username" field = branch admin code
    admin = db.query(User).filter(
        User.user_code == form.username.strip(),
        User.role == "branch_admin",
        User.is_deleted == False,
    ).first()

    verify_login(
        db, admin, form.password, "Incorrect admin code or password",
        request=request, expected_role="branch_admin",
    )

    if not admin.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=admin,
            details="Account is disabled", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is disabled. Contact superadmin")

    branch = db.query(Branch).filter(Branch.id == admin.branch_id).first()
    if not branch or branch.is_deleted or not branch.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=admin,
            details="Branch is inactive or unavailable", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your branch is inactive. Contact superadmin")

    add_security_event(db, event_type="login_success", succeeded=True, user=admin, request=request)
    db.commit()
    return TokenResponse(access_token=create_access_token(admin.id, admin.role))


@router.get("/me", response_model=BranchAdminMeOut)
def branch_admin_me(
    current_user: User = Depends(require_roles("branch_admin")),
    db: Session = Depends(get_db),
):
    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")

    return {
        "id": current_user.id,
        "user_code": current_user.user_code,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "contact_number": current_user.contact_number,
        "role": current_user.role,
        "branch_id": current_user.branch_id,
        "branch": branch,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }