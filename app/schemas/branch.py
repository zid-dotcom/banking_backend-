import re

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def normalize_ifsc(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value):
        raise ValueError("IFSC must look like SBIN0001234")
    return value


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    ifsc_code: str
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=255)
    contact_number: str

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, value: str) -> str:
        return normalize_ifsc(value)

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\+?\d{10,14}", v):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return v


class BranchOut(BaseModel):
    id: int
    branch_code: str
    ifsc_code: str | None
    name: str
    city: str
    state: str
    address: str
    contact_number: str
    opening_date: date
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    ifsc_code: str | None = None
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = Field(default=None, min_length=5, max_length=255)
    contact_number: str | None = None

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_ifsc(value)

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not re.fullmatch(r"\+?\d{10,14}", v):
            raise ValueError("Contact number must be 10 to 14 digits, optional + at start")
        return v


class BranchStatusUpdate(BaseModel):
    is_active: bool