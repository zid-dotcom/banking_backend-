import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_roles
from app.core.security_events import add_security_event
from app.models.branch import Branch
from app.models.user import User
from app.schemas.branch_admin import (
    BranchAdminCreate,
    BranchAdminOut,
    BranchAdminStatusUpdate,
    BranchAdminUpdate,
)

router = APIRouter(prefix="/superadmin/branch-admins", tags=["Superadmin - Branch Admins"])


def generate_user_code(db: Session) -> str:
    for _ in range(20):
        code = str(secrets.randbelow(900000) + 100000)
        if not db.query(User).filter(User.user_code == code).first():
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate unique user code",
    )


def get_branch_admin_or_404(db: Session, admin_id: int) -> User:
    admin = db.query(User).filter(
        User.id == admin_id,
        User.role == "branch_admin",
        User.is_deleted == False,
    ).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch admin not found")
    return admin


@router.post("", response_model=BranchAdminOut, status_code=status.HTTP_201_CREATED)
def create_branch_admin(
    data: BranchAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = db.query(Branch).filter(Branch.id == data.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    if not branch.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is inactive")

    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    admin = User(
        user_code=generate_user_code(db),
        full_name=data.full_name,
        email=email,
        hashed_password=hash_password(data.password),
        contact_number=data.contact_number,
        role="branch_admin",
        branch_id=data.branch_id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.get("", response_model=List[BranchAdminOut])
def list_branch_admins(
    skip: int = 0,
    limit: int = 20,
    branch_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(User).filter(User.role == "branch_admin", User.is_deleted == False)
    if branch_id is not None:
        query = query.filter(User.branch_id == branch_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            User.full_name.ilike(like),
            User.email.ilike(like),
            User.user_code.ilike(like),
        ))
    return query.order_by(User.id).offset(skip).limit(limit).all()


@router.get("/{admin_id}", response_model=BranchAdminOut)
def get_branch_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return get_branch_admin_or_404(db, admin_id)


@router.put("/{admin_id}", response_model=BranchAdminOut)
def update_branch_admin(
    admin_id: int,
    request: Request,
    data: BranchAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    admin = get_branch_admin_or_404(db, admin_id)

    changes = data.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "branch_id" in changes:
        branch = db.query(Branch).filter(
            Branch.id == changes["branch_id"], Branch.is_deleted == False
        ).first()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        if not branch.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is inactive")

    if "password" in changes:
        admin.hashed_password = hash_password(changes.pop("password"))
        admin.failed_attempts = 0
        admin.locked_until = None

    for field, value in changes.items():
        setattr(admin, field, value)

    if "password" in data.model_fields_set:
        add_security_event(
            db, event_type="password_reset", succeeded=True, user=admin,
            actor=current_user, details="Password reset by superadmin",
            request=request,
        )
    db.commit()
    db.refresh(admin)
    return admin


@router.patch("/{admin_id}/unlock")
def unlock_branch_admin(
    admin_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    admin = get_branch_admin_or_404(db, admin_id)
    admin.failed_attempts = 0
    admin.locked_until = None
    add_security_event(
        db, event_type="account_unlocked", succeeded=True, user=admin,
        actor=current_user, details="Account unlocked by superadmin",
        request=request,
    )
    db.commit()
    return {"message": "Branch admin unlocked", "user_code": admin.user_code}


@router.patch("/{admin_id}/status", response_model=BranchAdminOut)
def change_branch_admin_status(
    admin_id: int,
    data: BranchAdminStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    admin = get_branch_admin_or_404(db, admin_id)

    if admin.is_active == data.is_active:
        state = "active" if data.is_active else "inactive"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch admin already {state}",
        )

    admin.is_active = data.is_active
    db.commit()
    db.refresh(admin)
    return admin


@router.delete("/{admin_id}")
def delete_branch_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    admin = get_branch_admin_or_404(db, admin_id)

    admin.is_deleted = True
    admin.deleted_at = datetime.now(timezone.utc)
    admin.is_active = False
    db.commit()

    return {"message": "Branch admin deleted", "user_code": admin.user_code}