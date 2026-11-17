import math
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security_events import add_security_event
from app.models.branch import Branch
from app.models.member import Member
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


def verify_login(
    db: Session,
    user: User | None,
    password: str,
    error_message: str,
    *,
    request: Request | None = None,
    expected_role: str | None = None,
    event_context: str = "login",
) -> None:
    now = datetime.now(timezone.utc)

    if user and user.locked_until and user.locked_until > now:
        minutes = math.ceil((user.locked_until - now).total_seconds() / 60)
        add_security_event(
            db,
            event_type=f"{event_context}_blocked",
            succeeded=False,
            user=user,
            is_suspicious=True,
            details="Login attempted while account was locked",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many wrong attempts. Try again after {minutes} minutes",
        )

    if not user or not verify_password(password, user.hashed_password):
        locked_out = False
        if user:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                user.failed_attempts = 0
                locked_out = True
        add_security_event(
            db,
            event_type=f"{event_context}_failure",
            succeeded=False,
            user=user,
            account_role=expected_role,
            is_suspicious=locked_out,
            details="Invalid credentials",
            request=request,
        )
        if locked_out:
            add_security_event(
                db,
                event_type="account_locked",
                succeeded=True,
                user=user,
                account_role=expected_role,
                is_suspicious=True,
                details=f"Locked after {MAX_FAILED_ATTEMPTS} failed attempts",
                request=request,
            )
        db.commit()
        if locked_out:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many wrong attempts. Account locked for {LOCK_MINUTES} minutes",
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, error_message)

    if user.failed_attempts or user.locked_until:
        user.failed_attempts = 0
        user.locked_until = None
        db.commit()


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active or user.is_deleted:
        raise credentials_error

    if user.role != "superadmin" and user.branch_id is not None:
        branch = db.query(Branch).filter(Branch.id == user.branch_id).first()
        if not branch or branch.is_deleted or not branch.is_active:
            raise credentials_error

    if user.role == "member":
        member = db.query(Member).filter(Member.user_id == user.id).first()
        if not member or member.status != "approved":
            raise credentials_error

    return user


def require_roles(*allowed_roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user
    return checker