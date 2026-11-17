from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.fd_mis_scheme import FdMisScheme
from app.models.user import User
from app.schemas.fd_mis_scheme import FdMisSchemeOut

router = APIRouter(
    prefix="/branch-admin/fd-mis-schemes",
    tags=["Branch Admin - FD/MIS Schemes"],
)


@router.get("", response_model=List[FdMisSchemeOut])
def list_available_fd_mis_schemes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = db.query(FdMisScheme).filter(
        FdMisScheme.is_active == True,
        FdMisScheme.is_deleted == False,
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            FdMisScheme.scheme_name.ilike(like) | FdMisScheme.scheme_code.ilike(like)
        )
    return query.order_by(FdMisScheme.scheme_name, FdMisScheme.id).offset(skip).limit(limit).all()
