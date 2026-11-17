from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.savings_scheme import SavingsScheme
from app.models.user import User
from app.schemas.savings_scheme import SavingsSchemeOut

router = APIRouter(
    prefix="/member/savings-schemes",
    tags=["Member - Savings Schemes"],
)


@router.get("", response_model=List[SavingsSchemeOut])
def list_available_savings_schemes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    query = db.query(SavingsScheme).filter(
        SavingsScheme.is_active == True,
        SavingsScheme.is_deleted == False,
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            SavingsScheme.scheme_name.ilike(like) | SavingsScheme.scheme_code.ilike(like)
        )
    return query.order_by(SavingsScheme.scheme_name, SavingsScheme.id).offset(skip).limit(limit).all()
