from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.loan_scheme import LoanScheme
from app.models.user import User
from app.schemas.loan_scheme import LoanSchemeOut

router = APIRouter(
    prefix="/branch-admin/loan-schemes",
    tags=["Branch Admin - Loan Schemes"],
)


@router.get("", response_model=List[LoanSchemeOut])
def list_available_loan_schemes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = db.query(LoanScheme).filter(
        LoanScheme.is_active == True,
        LoanScheme.is_deleted == False,
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            LoanScheme.scheme_name.ilike(like) | LoanScheme.scheme_code.ilike(like)
        )
    return query.order_by(LoanScheme.scheme_name, LoanScheme.id).offset(skip).limit(limit).all()
