from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.staff_role import StaffRoleOut

router = APIRouter(
    prefix="/branch-admin/staff-roles",
    tags=["Branch Admin - Staff Roles"],
)


@router.get("", response_model=List[StaffRoleOut])
def list_available_staff_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = db.query(StaffRole).filter(StaffRole.is_deleted == False)
    if search:
        query = query.filter(StaffRole.name.ilike(f"%{search.strip()}%"))
    return query.order_by(StaffRole.name, StaffRole.id).offset(skip).limit(limit).all()
