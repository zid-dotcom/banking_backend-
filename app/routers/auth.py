from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_events import add_security_event
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
    verify_login,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/superadmin/login", response_model=TokenResponse)
def superadmin_login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form.username, User.role == "superadmin").first()

    verify_login(
        db, user, form.password, "Incorrect email or password",
        request=request, expected_role="superadmin",
    )
    if not user.is_active:
        add_security_event(
            db, event_type="login_denied", succeeded=False, user=user,
            details="Account is disabled", request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    add_security_event(
        db, event_type="login_success", succeeded=True, user=user, request=request,
    )
    db.commit()
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/superadmin/ping")
def superadmin_only(user: User = Depends(require_roles("superadmin"))):
    return {"message": f"Hello {user.full_name}, you are a superadmin"}


@router.post("/change-password")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        add_security_event(
            db, event_type="password_change_failure", succeeded=False,
            user=current_user, is_suspicious=True,
            details="Current password validation failed", request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )

    current_user.hashed_password = hash_password(data.new_password)
    add_security_event(
        db, event_type="password_changed", succeeded=True, user=current_user,
        request=request,
    )
    db.commit()
    return {"message": "Password changed successfully"}