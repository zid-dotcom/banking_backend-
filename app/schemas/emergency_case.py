from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmergencyCaseCreate(BaseModel):
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


class EmergencyMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class EmergencyBranchOut(BaseModel):
    id: int
    branch_code: str
    name: str
    city: str
    state: str
    address: str

    model_config = ConfigDict(from_attributes=True)


class EmergencyUserOut(BaseModel):
    id: int
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class EmergencyMessageOut(BaseModel):
    id: int
    sender: EmergencyUserOut
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmergencyCaseListOut(BaseModel):
    id: int
    subject: str
    branch: EmergencyBranchOut
    created_by: EmergencyUserOut
    unread_count: int
    created_at: datetime
    updated_at: datetime


class EmergencyCaseDetailOut(EmergencyCaseListOut):
    messages: list[EmergencyMessageOut]


class EmergencyBranchUnreadCountOut(BaseModel):
    branch_id: int
    branch_name: str
    city: str
    state: str
    unread_count: int


class SuperadminEmergencyUnreadCountOut(BaseModel):
    total_unread_count: int
    branches: list[EmergencyBranchUnreadCountOut]


class BranchAdminEmergencyUnreadCountOut(BaseModel):
    unread_count: int
