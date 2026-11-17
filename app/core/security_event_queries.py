from datetime import datetime
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app.models.branch import Branch
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.schemas.security_event import SecurityEventOut


def query_security_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    branch_id: int | None = None,
    user_id: int | None = None,
    role: str | None = None,
    event_type: str | None = None,
    succeeded: bool | None = None,
    suspicious_only: bool = False,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    search: str | None = None,
) -> List[SecurityEventOut]:
    event_user = aliased(User)
    actor_user = aliased(User)
    query = (
        db.query(SecurityEvent, event_user, actor_user, Branch)
        .outerjoin(event_user, SecurityEvent.user_id == event_user.id)
        .outerjoin(actor_user, SecurityEvent.actor_user_id == actor_user.id)
        .outerjoin(Branch, SecurityEvent.branch_id == Branch.id)
    )
    if branch_id is not None:
        query = query.filter(SecurityEvent.branch_id == branch_id)
    if user_id is not None:
        query = query.filter(SecurityEvent.user_id == user_id)
    if role:
        query = query.filter(SecurityEvent.account_role == role.strip().lower())
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type.strip().lower())
    if succeeded is not None:
        query = query.filter(SecurityEvent.succeeded == succeeded)
    if suspicious_only:
        query = query.filter(SecurityEvent.is_suspicious == True)
    if from_date is not None:
        query = query.filter(SecurityEvent.created_at >= from_date)
    if to_date is not None:
        query = query.filter(SecurityEvent.created_at <= to_date)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(
            event_user.full_name.ilike(like),
            event_user.user_code.ilike(like),
            SecurityEvent.details.ilike(like),
            SecurityEvent.ip_address.ilike(like),
        ))

    rows = (
        query.order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        SecurityEventOut(
            id=event.id,
            user_id=event.user_id,
            user_code=user.user_code if user else None,
            user_name=user.full_name if user else None,
            actor_user_id=event.actor_user_id,
            actor_name=actor.full_name if actor else None,
            account_role=event.account_role,
            branch_id=event.branch_id,
            branch_name=branch.name if branch else None,
            event_type=event.event_type,
            succeeded=event.succeeded,
            is_suspicious=event.is_suspicious,
            details=event.details,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            created_at=event.created_at,
        )
        for event, user, actor, branch in rows
    ]
