from fastapi import Request
from sqlalchemy.orm import Session

from app.models.security_event import SecurityEvent
from app.models.user import User


def add_security_event(
    db: Session,
    *,
    event_type: str,
    succeeded: bool,
    user: User | None = None,
    account_role: str | None = None,
    branch_id: int | None = None,
    actor: User | None = None,
    is_suspicious: bool = False,
    details: str | None = None,
    request: Request | None = None,
) -> None:
    client = request.client if request else None
    user_agent = request.headers.get("user-agent") if request else None
    db.add(SecurityEvent(
        user_id=user.id if user else None,
        actor_user_id=actor.id if actor else None,
        branch_id=branch_id if branch_id is not None else (user.branch_id if user else None),
        account_role=account_role or (user.role if user else None),
        event_type=event_type,
        succeeded=succeeded,
        is_suspicious=is_suspicious,
        details=details,
        ip_address=client.host if client else None,
        user_agent=user_agent[:512] if user_agent else None,
    ))
