from datetime import datetime

from pydantic import BaseModel


class SecurityEventOut(BaseModel):
    id: int
    user_id: int | None
    user_code: str | None
    user_name: str | None
    actor_user_id: int | None
    actor_name: str | None
    account_role: str | None
    branch_id: int | None
    branch_name: str | None
    event_type: str
    succeeded: bool
    is_suspicious: bool
    details: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class SecurityEventBranchSummary(BaseModel):
    branch_id: int | None
    branch_name: str
    event_count: int
    suspicious_count: int


class SecurityEventSummaryOut(BaseModel):
    total_events: int
    suspicious_events: int
    branches: list[SecurityEventBranchSummary]


