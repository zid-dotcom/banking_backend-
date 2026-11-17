import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.branch import BranchOut


class BranchAdminCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    contact_number: str
    branch_id: int

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\+?\d{10,14}", v):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return v


class BranchAdminOut(BaseModel):
    id: int
    user_code: str
    full_name: str
    email: EmailStr
    contact_number: str
    role: str
    branch_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BranchAdminMeOut(BranchAdminOut):
    branch: BranchOut


class BranchAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    contact_number: str | None = None
    branch_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not re.fullmatch(r"\+?\d{10,14}", v):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return v


class BranchAdminStatusUpdate(BaseModel):
    is_active: bool