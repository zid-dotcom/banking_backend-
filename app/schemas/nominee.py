import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class NomineeCreate(BaseModel):
    nominee_name: str = Field(min_length=2, max_length=100)
    relationship_type: str = Field(min_length=2, max_length=30)
    date_of_birth: date

    @field_validator("relationship_type")
    @classmethod
    def check_relationship(cls, v: str) -> str:
        v = " ".join(v.split())
        if not re.fullmatch(r"[A-Za-z][A-Za-z -]{1,29}", v):
            raise ValueError("Relationship must be 2 to 30 letters")
        return v.title()

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v: date) -> date:
        today = date.today()
        if v >= today:
            raise ValueError("Date of birth must be in the past")
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Nominee must be at least 18 years old")
        return v


class NomineeOut(BaseModel):
    id: int
    nominee_name: str
    relationship_type: str
    date_of_birth: date
    status: str
    rejection_reason: str | None
    submitted_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}