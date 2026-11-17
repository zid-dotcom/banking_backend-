from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.fd_mis_scheme import FdMisScheme
from app.models.user import User
from app.schemas.fd_mis_scheme import (
    FdMisSchemeCreate,
    FdMisSchemeOut,
    FdMisSchemeStatusUpdate,
    FdMisSchemeUpdate,
)

router = APIRouter(prefix="/superadmin/fd-mis-schemes", tags=["Superadmin - FD/MIS Schemes"])


def get_scheme_or_404(db: Session, scheme_id: int) -> FdMisScheme:
    scheme = db.query(FdMisScheme).filter(
        FdMisScheme.id == scheme_id,
        FdMisScheme.is_deleted == False,
    ).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FD/MIS scheme not found")
    return scheme


@router.post("", response_model=FdMisSchemeOut, status_code=status.HTTP_201_CREATED)
def create_fd_mis_scheme(
    data: FdMisSchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = FdMisScheme(**data.model_dump())
    db.add(scheme)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A non-deleted FD/MIS scheme with this code already exists",
        ) from error
    db.refresh(scheme)
    return scheme


@router.get("", response_model=List[FdMisSchemeOut])
def list_fd_mis_schemes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(FdMisScheme).filter(FdMisScheme.is_deleted == False)
    if is_active is not None:
        query = query.filter(FdMisScheme.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            FdMisScheme.scheme_name.ilike(like) | FdMisScheme.scheme_code.ilike(like)
        )
    return query.order_by(FdMisScheme.scheme_name, FdMisScheme.id).offset(skip).limit(limit).all()


@router.get("/{scheme_id}", response_model=FdMisSchemeOut)
def get_fd_mis_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return get_scheme_or_404(db, scheme_id)


@router.put("/{scheme_id}", response_model=FdMisSchemeOut)
def update_fd_mis_scheme(
    scheme_id: int,
    data: FdMisSchemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = get_scheme_or_404(db, scheme_id)
    for field, value in data.model_dump().items():
        setattr(scheme, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A non-deleted FD/MIS scheme with this code already exists",
        ) from error
    db.refresh(scheme)
    return scheme


@router.patch("/{scheme_id}/status", response_model=FdMisSchemeOut)
def change_fd_mis_scheme_status(
    scheme_id: int,
    data: FdMisSchemeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = get_scheme_or_404(db, scheme_id)
    scheme.is_active = data.is_active
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}")
def delete_fd_mis_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = get_scheme_or_404(db, scheme_id)
    scheme.is_deleted = True
    scheme.deleted_at = datetime.now(timezone.utc)
    scheme.is_active = False
    db.commit()
    return {
        "message": "FD/MIS scheme deleted",
        "id": scheme.id,
        "scheme_code": scheme.scheme_code,
    }
