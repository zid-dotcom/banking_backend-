from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_event_queries import query_security_events
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.schemas.security_event import (
    SecurityEventBranchSummary,
    SecurityEventOut,
    SecurityEventSummaryOut,
)

router = APIRouter(
    prefix="/superadmin/security-events",
    tags=["Superadmin - Security Events"],
)


@router.get("", response_model=List[SecurityEventOut])
def list_security_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    branch_id: int | None = Query(default=None, gt=0),
    user_id: int | None = Query(default=None, gt=0),
    role: str | None = None,
    event_type: str | None = None,
    succeeded: bool | None = None,
    suspicious_only: bool = False,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return query_security_events(
        db,
        skip=skip,
        limit=limit,
        branch_id=branch_id,
        user_id=user_id,
        role=role,
        event_type=event_type,
        succeeded=succeeded,
        suspicious_only=suspicious_only,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )


@router.get("/summary", response_model=SecurityEventSummaryOut)
def get_security_event_summary(
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(SecurityEvent)
    if from_date is not None:
        query = query.filter(SecurityEvent.created_at >= from_date)
    if to_date is not None:
        query = query.filter(SecurityEvent.created_at <= to_date)

    total_events, suspicious_events = query.with_entities(
        func.count(SecurityEvent.id),
        func.count(SecurityEvent.id).filter(SecurityEvent.is_suspicious == True),
    ).one()

    rows = (
        query.outerjoin(Branch, SecurityEvent.branch_id == Branch.id)
        .with_entities(
            SecurityEvent.branch_id,
            Branch.name,
            func.count(SecurityEvent.id),
            func.count(SecurityEvent.id).filter(SecurityEvent.is_suspicious == True),
        )
        .group_by(SecurityEvent.branch_id, Branch.name)
        .order_by(Branch.name)
        .all()
    )
    return SecurityEventSummaryOut(
        total_events=total_events,
        suspicious_events=suspicious_events,
        branches=[
            SecurityEventBranchSummary(
                branch_id=branch_id,
                branch_name=branch_name or "Unassigned",
                event_count=event_count,
                suspicious_count=suspicious_count,
            )
            for branch_id, branch_name, event_count, suspicious_count in rows
        ],
    )
