from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.core.security_event_queries import query_security_events
from app.models.user import User
from app.schemas.security_event import SecurityEventOut

router = APIRouter(
    prefix="/branch-admin/security-events",
    tags=["Branch Admin - Security Events"],
)


@router.get("", response_model=List[SecurityEventOut])
def list_branch_security_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    user_id: int | None = Query(default=None, gt=0),
    role: str | None = None,
    event_type: str | None = None,
    succeeded: bool | None = None,
    suspicious_only: bool = False,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Branch admin is not assigned to a branch",
        )
    return query_security_events(
        db,
        skip=skip,
        limit=limit,
        branch_id=current_user.branch_id,
        user_id=user_id,
        role=role,
        event_type=event_type,
        succeeded=succeeded,
        suspicious_only=suspicious_only,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )
