import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_roles
from app.core.security_events import add_security_event
from app.models.staff import Staff
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.branch_staff import (
    BranchStaffCreate,
    BranchStaffOut,
    BranchStaffStatusUpdate,
    BranchStaffUpdate,
)

router = APIRouter(prefix="/branch-admin/staff", tags=["Branch Admin - Staff"])


def generate_staff_code(db: Session) -> str:
    for _ in range(20):
        code = str(secrets.randbelow(900000) + 100000)
        if not db.query(User.id).filter(User.user_code == code).first():
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate unique staff code",
    )


def get_staff_or_404(db: Session, staff_id: int, branch_id: int) -> tuple[Staff, User, StaffRole]:
    row = (
        db.query(Staff, User, StaffRole)
        .join(User, Staff.user_id == User.id)
        .join(StaffRole, Staff.staff_role_id == StaffRole.id)
        .filter(
            Staff.id == staff_id,
            User.role == "staff",
            User.branch_id == branch_id,
            User.is_deleted == False,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return row


def to_staff_out(staff: Staff, user: User, staff_role: StaffRole) -> BranchStaffOut:
    return BranchStaffOut(
        id=staff.id,
        staff_code=user.user_code,
        full_name=user.full_name,
        email=user.email,
        contact_number=user.contact_number,
        address=staff.address,
        staff_role_id=staff_role.id,
        staff_role_name=staff_role.name,
        is_active=user.is_active,
        created_at=staff.created_at,
    )


def get_active_staff_role_or_404(db: Session, role_id: int) -> StaffRole:
    role = db.query(StaffRole).filter(
        StaffRole.id == role_id,
        StaffRole.is_deleted == False,
    ).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active staff role not found")
    return role


@router.post("", response_model=BranchStaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    data: BranchStaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    staff_role = get_active_staff_role_or_404(db, data.staff_role_id)
    email = str(data.email).lower()
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        user_code=generate_staff_code(db),
        full_name=data.full_name,
        email=email,
        hashed_password=hash_password(data.password),
        contact_number=data.contact_number,
        role="staff",
        branch_id=current_user.branch_id,
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
        staff = Staff(
            user_id=user.id,
            staff_role_id=staff_role.id,
            address=data.address,
        )
        db.add(staff)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or staff code already exists",
        ) from error
    db.refresh(staff)
    db.refresh(user)
    return to_staff_out(staff, user, staff_role)


@router.get("", response_model=List[BranchStaffOut])
def list_staff(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    staff_role_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        db.query(Staff, User, StaffRole)
        .join(User, Staff.user_id == User.id)
        .join(StaffRole, Staff.staff_role_id == StaffRole.id)
        .filter(
            User.role == "staff",
            User.branch_id == current_user.branch_id,
            User.is_deleted == False,
        )
    )
    if staff_role_id is not None:
        query = query.filter(Staff.staff_role_id == staff_role_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(
            User.full_name.ilike(like),
            User.email.ilike(like),
            User.user_code.ilike(like),
            User.contact_number.ilike(like),
        ))

    rows = query.order_by(Staff.id.desc()).offset(skip).limit(limit).all()
    return [to_staff_out(staff, user, role) for staff, user, role in rows]


@router.get("/{staff_id}", response_model=BranchStaffOut)
def get_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    return to_staff_out(*get_staff_or_404(db, staff_id, current_user.branch_id))


@router.put("/{staff_id}", response_model=BranchStaffOut)
def update_staff(
    staff_id: int,
    request: Request,
    data: BranchStaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    staff, user, current_role = get_staff_or_404(db, staff_id, current_user.branch_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).lower()
        duplicate = db.query(User.id).filter(User.email == email, User.id != user.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user.email = email

    if "staff_role_id" in changes and changes["staff_role_id"] is not None:
        current_role = get_active_staff_role_or_404(db, changes["staff_role_id"])
        staff.staff_role_id = current_role.id

    if "password" in changes and changes["password"] is not None:
        user.hashed_password = hash_password(changes["password"])
        user.failed_attempts = 0
        user.locked_until = None
        add_security_event(
            db, event_type="password_reset", succeeded=True, user=user,
            actor=current_user, details="Password reset by branch admin",
            request=request,
        )

    for field in ("full_name", "contact_number"):
        if field in changes and changes[field] is not None:
            setattr(user, field, changes[field])
    if "address" in changes and changes["address"] is not None:
        staff.address = changes["address"]

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from error
    db.refresh(staff)
    db.refresh(user)
    return to_staff_out(staff, user, current_role)


@router.patch("/{staff_id}/status", response_model=BranchStaffOut)
def change_staff_status(
    staff_id: int,
    data: BranchStaffStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    staff, user, staff_role = get_staff_or_404(db, staff_id, current_user.branch_id)
    if user.is_active == data.is_active:
        state = "active" if data.is_active else "inactive"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Staff member already {state}")

    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return to_staff_out(staff, user, staff_role)


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    staff, user, _ = get_staff_or_404(db, staff_id, current_user.branch_id)
    user.is_deleted = True
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    db.commit()
    return {"message": "Staff member deleted", "staff_code": user.user_code}
