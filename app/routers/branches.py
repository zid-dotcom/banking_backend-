import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.user import User
from app.schemas.branch import BranchCreate, BranchOut, BranchUpdate, BranchStatusUpdate

router = APIRouter(prefix="/superadmin/branches", tags=["Superadmin - Branches"])

def generate_branch_code(db: Session) -> str:
    for _ in range(20):
        code = str(secrets.randbelow(900000) + 100000)  # 100000 to 999999
        if not db.query(Branch).filter(Branch.branch_code == code).first():
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate unique branch code",
    )

def get_branch_or_404(db: Session, branch_id: int) -> Branch:
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return branch


@router.post("", response_model=BranchOut, status_code=status.HTTP_201_CREATED)
def create_branch(
    data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = Branch(
        branch_code=generate_branch_code(db),
        ifsc_code=data.ifsc_code,
        name=data.name,
        city=data.city,
        state=data.state,
        address=data.address,
        contact_number=data.contact_number,
    )
    db.add(branch)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Branch code or IFSC already exists",
        ) from error
    db.refresh(branch)
    return branch

@router.get("", response_model=List[BranchOut])
def list_branches(
    skip: int = 0,
    limit: int = 20,
    city: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(Branch).filter(Branch.is_deleted == False)
    if city:
        query = query.filter(Branch.city.ilike(f"%{city}%"))
    if is_active is not None:
        query = query.filter(Branch.is_active == is_active)
    return query.order_by(Branch.id).offset(skip).limit(limit).all()


@router.get("/{branch_id}", response_model=BranchOut)
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return get_branch_or_404(db, branch_id)


@router.put("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = get_branch_or_404(db, branch_id)

    changes = data.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    for field, value in changes.items():
        setattr(branch, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IFSC already assigned to another branch",
        ) from error
    db.refresh(branch)
    return branch



@router.patch("/{branch_id}/status", response_model=BranchOut)
def change_branch_status(
    branch_id: int,
    data: BranchStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = get_branch_or_404(db, branch_id)

    if branch.is_active == data.is_active:
        state = "active" if data.is_active else "inactive"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Branch already {state}")

    branch.is_active = data.is_active
    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/{branch_id}")
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    branch = get_branch_or_404(db, branch_id)

    branch.is_deleted = True
    branch.deleted_at = datetime.now(timezone.utc)
    branch.is_active = False
    db.commit()

    return {"message": "Branch deleted", "branch_code": branch.branch_code}