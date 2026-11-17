from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NomineeChangeRequestStatus = Literal["pending", "approved", "rejected"]


class NomineeChangeRequestCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=150)
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Subject must contain at least 2 characters")
        return value

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class NomineeChangeRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    rejection_reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.status == "rejected":
            reason = (self.rejection_reason or "").strip()
            if len(reason) < 5:
                raise ValueError("A rejection reason of at least 5 characters is required")
            self.rejection_reason = reason
        else:
            self.rejection_reason = None
        return self


class NomineeChangeRequestOut(BaseModel):
    id: int
    subject: str
    message: str
    status: NomineeChangeRequestStatus
    rejection_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    consumed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BranchAdminNomineeChangeRequestOut(NomineeChangeRequestOut):
    member_id: int
    member_code: str
    member_name: str
    branch_id: int
    branch_name: str
