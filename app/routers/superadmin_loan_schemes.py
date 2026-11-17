from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.loan_scheme import LoanScheme
from app.models.user import User
from app.schemas.loan_scheme import (
    LoanSchemeCreate,
    LoanSchemeOut,
    LoanSchemeStatusUpdate,
    LoanSchemeUpdate,
)

router = APIRouter(prefix="/superadmin/loan-schemes", tags=["Superadmin - Loan Schemes"])


def get_scheme_or_404(db: Session, scheme_id: int) -> LoanScheme:
    scheme = db.query(LoanScheme).filter(
        LoanScheme.id == scheme_id,
        LoanScheme.is_deleted == False,
    ).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan scheme not found")
    return scheme


@router.post("", response_model=LoanSchemeOut, status_code=status.HTTP_201_CREATED)
def create_loan_scheme(
    data: LoanSchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = LoanScheme(**data.model_dump())
    db.add(scheme)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active loan scheme with this code already exists",
        ) from error
    db.refresh(scheme)
    return scheme


@router.get("", response_model=List[LoanSchemeOut])
def list_loan_schemes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(LoanScheme).filter(LoanScheme.is_deleted == False)
    if is_active is not None:
        query = query.filter(LoanScheme.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            LoanScheme.scheme_name.ilike(like) | LoanScheme.scheme_code.ilike(like)
        )
    return query.order_by(LoanScheme.scheme_name, LoanScheme.id).offset(skip).limit(limit).all()


@router.get("/{scheme_id}", response_model=LoanSchemeOut)
def get_loan_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return get_scheme_or_404(db, scheme_id)


@router.put("/{scheme_id}", response_model=LoanSchemeOut)
def update_loan_scheme(
    scheme_id: int,
    data: LoanSchemeUpdate,
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
            detail="An active loan scheme with this code already exists",
        ) from error
    db.refresh(scheme)
    return scheme


@router.patch("/{scheme_id}/status", response_model=LoanSchemeOut)
def change_loan_scheme_status(
    scheme_id: int,
    data: LoanSchemeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    scheme = get_scheme_or_404(db, scheme_id)
    scheme.is_active = data.is_active
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}")
def delete_loan_scheme(
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
        "message": "Loan scheme deleted",
        "id": scheme.id,
        "scheme_code": scheme.scheme_code,
    }
