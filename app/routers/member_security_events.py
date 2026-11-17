from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.core.security_event_queries import query_security_events
from app.models.user import User
from app.schemas.security_event import SecurityEventOut

router = APIRouter(
    prefix="/member/security-events",
    tags=["Member - Security Events"],
)


@router.get("", response_model=List[SecurityEventOut])
def list_member_security_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = None,
    succeeded: bool | None = None,
    suspicious_only: bool = False,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    return query_security_events(
        db,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        event_type=event_type,
        succeeded=succeeded,
        suspicious_only=suspicious_only,
        from_date=from_date,
        to_date=to_date,
    )
