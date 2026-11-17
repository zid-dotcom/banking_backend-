from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.staff_role import StaffRole
from app.models.user import User
from app.schemas.staff_role import StaffRoleCreate, StaffRoleOut

router = APIRouter(prefix="/superadmin/staff-roles", tags=["Superadmin - Staff Roles"])


@router.post("", response_model=StaffRoleOut, status_code=status.HTTP_201_CREATED)
def create_staff_role(
    data: StaffRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    role = StaffRole(name=data.name, description=data.description)
    db.add(role)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active staff role with this name already exists",
        ) from error
    db.refresh(role)
    return role


@router.get("", response_model=List[StaffRoleOut])
def list_staff_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(StaffRole).filter(StaffRole.is_deleted == False)
    if search:
        query = query.filter(StaffRole.name.ilike(f"%{search.strip()}%"))
    return query.order_by(StaffRole.name, StaffRole.id).offset(skip).limit(limit).all()


@router.delete("/{role_id}")
def delete_staff_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    role = db.query(StaffRole).filter(
        StaffRole.id == role_id,
        StaffRole.is_deleted == False,
    ).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff role not found")

    role.is_deleted = True
    role.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Staff role deleted", "id": role.id, "name": role.name}
