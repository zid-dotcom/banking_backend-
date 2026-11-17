from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.staff import Staff
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.superadmin_staff import SuperadminStaffOut

router = APIRouter(prefix="/superadmin/staff", tags=["Superadmin - Staff"])


@router.get("", response_model=List[SuperadminStaffOut])
def list_staff_for_superadmin(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    branch_id: int | None = Query(default=None, gt=0),
    staff_role_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = (
        db.query(Staff, User, StaffRole, Branch)
        .join(User, Staff.user_id == User.id)
        .join(StaffRole, Staff.staff_role_id == StaffRole.id)
        .join(Branch, User.branch_id == Branch.id)
        .filter(
            User.role == "staff",
            User.is_deleted == False,
            Branch.is_deleted == False,
        )
    )
    if branch_id is not None:
        query = query.filter(User.branch_id == branch_id)
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
            StaffRole.name.ilike(like),
            Branch.name.ilike(like),
            Branch.branch_code.ilike(like),
        ))

    rows = query.order_by(Branch.name, Staff.id.desc()).offset(skip).limit(limit).all()
    return [
        SuperadminStaffOut(
            id=staff.id,
            staff_code=user.user_code,
            full_name=user.full_name,
            email=user.email,
            contact_number=user.contact_number,
            address=staff.address,
            staff_role_id=staff_role.id,
            staff_role_name=staff_role.name,
            branch_id=branch.id,
            branch_code=branch.branch_code,
            branch_name=branch.name,
            is_active=user.is_active,
            branch_is_active=branch.is_active,
            created_at=staff.created_at,
        )
        for staff, user, staff_role, branch in rows
    ]
