from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NomineeListOut(BaseModel):
    id: int
    member_code: str
    member_name: str
    nominee_name: str
    relationship_type: str
    status: str
    submitted_at: datetime


class NomineeDetailOut(BaseModel):
    id: int
    member_code: str
    member_name: str
    nominee_name: str
    relationship_type: str
    date_of_birth: date
    aadhaar_front_url: str
    aadhaar_back_url: str
    status: str
    rejection_reason: str | None
    submitted_at: datetime
    reviewed_at: datetime | None


class NomineeStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    rejection_reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def check_reason(self):
        if self.status == "rejected":
            reason = (self.rejection_reason or "").strip()
            if len(reason) < 5:
                raise ValueError("Rejection reason is required (min 5 characters)")
            self.rejection_reason = reason
        else:
            self.rejection_reason = None
        return self
