from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.branch import BranchOut


class MemberNomineeOut(BaseModel):
    status: str
    nominee_name: str | None = None
    relationship_type: str | None = None
    date_of_birth: date | None = None
    aadhaar_front_url: str | None = None
    aadhaar_back_url: str | None = None
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None


class MemberListOut(BaseModel):
    id: int
    member_code: str
    full_name: str
    email: EmailStr
    mobile: str
    city: str
    status: str
    is_active: bool
    created_at: datetime
    nominee: MemberNomineeOut


class MemberDetailOut(BaseModel):
    id: int
    member_code: str
    full_name: str
    email: EmailStr
    mobile: str
    branch_id: int
    date_of_birth: date
    gender: str
    country: str
    state: str
    district: str
    city: str
    street: str
    building_no: str
    zip_code: str
    aadhaar_number: str
    pan_number: str
    bank_holder_name: str
    bank_account_number: str
    ifsc_code: str
    aadhaar_front_url: str
    aadhaar_back_url: str
    pan_image_url: str
    passbook_image_url: str
    status: str
    rejection_reason: str | None
    reviewed_at: datetime | None
    is_active: bool
    created_at: datetime
    nominee: MemberNomineeOut


class MemberStatusUpdate(BaseModel):
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


class MemberActiveUpdate(BaseModel):
    is_active: bool


class MemberPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=72)


class SuperadminBranchMembersOut(BaseModel):
    branch: BranchOut
    members: list[MemberDetailOut]