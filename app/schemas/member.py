import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PAN_HOLDER_TYPES = "PCHFATBLJG"

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


class MemberRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str
    branch_id: int
    date_of_birth: date
    gender: Literal["Male", "Female", "Other"]
    country: Literal["India", "UAE", "USA", "UK", "Canada", "Australia", "Other"]
    state: str = Field(min_length=2, max_length=100)
    district: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    street: str = Field(min_length=2, max_length=150)
    building_no: str = Field(min_length=1, max_length=50)
    zip_code: str
    mobile: str
    aadhaar_number: str
    pan_number: str
    bank_holder_name: str = Field(min_length=2, max_length=100)
    bank_account_number: str
    ifsc_code: str

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\+?\d{10,14}", v):
            raise ValueError("Mobile must be 10 to 14 digits, optional + at start")
        return v

    @field_validator("zip_code")
    @classmethod
    def check_zip(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9 -]{3,10}", v):
            raise ValueError("ZIP code must be 3 to 10 letters or digits")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if v > today:
            raise ValueError("Date of birth cannot be in the future")
        if age < 18:
            raise ValueError("Member must be at least 18 years old")
        return v

    @field_validator("aadhaar_number")
    @classmethod
    def check_aadhaar(cls, v: str) -> str:
        v = re.sub(r"[\s-]", "", v)
        if not re.fullmatch(r"[2-9]\d{11}", v):
            raise ValueError("Aadhaar must be 12 digits and cannot start with 0 or 1")
        if not verhoeff_valid(v):
            raise ValueError("Aadhaar number is invalid")
        return v

    @field_validator("pan_number")
    @classmethod
    def check_pan(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v) or v[3] not in PAN_HOLDER_TYPES:
            raise ValueError("PAN must look like ABCPE1234F")
        return v

    @field_validator("bank_account_number")
    @classmethod
    def check_account(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"\d{9,18}", v):
            raise ValueError("Account number must be 9 to 18 digits")
        return v

    @field_validator("ifsc_code")
    @classmethod
    def check_ifsc(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", v):
            raise ValueError("IFSC must look like SBIN0001234")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class MemberRegisterResponse(BaseModel):
    message: str
    member_code: str
    status: str


class BranchPublic(BaseModel):
    id: int
    branch_code: str
    ifsc_code: str | None
    name: str
    city: str
    state: str

    model_config = {"from_attributes": True}

class MemberMeOut(BaseModel):
    member_code: str
    full_name: str
    email: EmailStr
    mobile: str
    branch_id: int
    branch: BranchPublic
    status: str


class MemberProfileOut(BaseModel):
    member_code: str
    full_name: str
    email: EmailStr
    mobile: str
    branch_id: int
    branch: BranchPublic
    date_of_birth: date
    gender: str
    country: str
    state: str
    district: str
    city: str
    street: str
    building_no: str
    zip_code: str
    aadhaar_masked: str
    pan_masked: str
    bank_holder_name: str
    bank_account_masked: str
    ifsc_code: str
    status: str


class MemberNomineeProfileOut(BaseModel):
    status: Literal["not_submitted", "pending", "approved", "rejected"]
    nominee_name: str | None = None
    relationship_type: str | None = None
    date_of_birth: date | None = None
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None


class MemberFullProfileOut(MemberProfileOut):
    kyc_status: str
    kyc_rejection_reason: str | None
    kyc_reviewed_at: datetime | None
    member_created_at: datetime
    nominee: MemberNomineeProfileOut