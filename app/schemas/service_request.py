from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ServiceRequestStatus = Literal["pending", "in_progress", "solved"]


class ServiceRequestCreate(BaseModel):
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


class ServiceRequestReplyCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reply cannot be empty")
        return value


class ServiceRequestStatusUpdate(BaseModel):
    status: ServiceRequestStatus


class ServiceRequestBranchOut(BaseModel):
    id: int
    branch_code: str
    name: str
    city: str
    state: str

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestMemberOut(BaseModel):
    id: int
    user_code: str | None
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestSenderOut(BaseModel):
    id: int
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestReplyOut(BaseModel):
    id: int
    sender: ServiceRequestSenderOut
    message: str
    created_at: datetime
    edited_at: datetime | None
    edited_by: ServiceRequestSenderOut | None

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestListOut(BaseModel):
    id: int
    branch: ServiceRequestBranchOut
    member: ServiceRequestMemberOut
    subject: str
    status: ServiceRequestStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceRequestDetailOut(ServiceRequestListOut):
    message: str
    replies: list[ServiceRequestReplyOut]
