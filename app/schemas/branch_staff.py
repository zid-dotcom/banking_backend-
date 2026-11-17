import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.branch import BranchOut


class BranchStaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    contact_number: str
    address: str = Field(min_length=5, max_length=255)
    staff_role_id: int = Field(gt=0)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"\+?\d{10,14}", value):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return value

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str) -> str:
        return " ".join(value.split())


class BranchStaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    contact_number: str | None = None
    address: str | None = Field(default=None, min_length=5, max_length=255)
    staff_role_id: int | None = Field(default=None, gt=0)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not re.fullmatch(r"\+?\d{10,14}", value):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return value

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class BranchStaffStatusUpdate(BaseModel):
    is_active: bool


class BranchStaffOut(BaseModel):
    id: int
    staff_code: str
    full_name: str
    email: EmailStr
    contact_number: str
    address: str
    staff_role_id: int
    staff_role_name: str
    is_active: bool
    created_at: datetime


class StaffRoleDetailsOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class StaffMeOut(BaseModel):
    staff_id: int
    user_id: int
    staff_code: str | None
    full_name: str
    email: EmailStr
    contact_number: str | None
    account_role: str
    staff_role: StaffRoleDetailsOut
    branch_id: int
    branch: BranchOut
    is_active: bool
    created_at: datetime
