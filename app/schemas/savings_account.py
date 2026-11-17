from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SavingsAccountOpeningRequestCreate(BaseModel):
    savings_scheme_id: int = Field(gt=0)


class SavingsAccountOpeningDecision(BaseModel):
    status: Literal["approved", "rejected"]
    rejection_reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.status == "rejected":
            reason = (self.rejection_reason or "").strip()
            if len(reason) < 5:
                raise ValueError("Rejection reason is required (min 5 characters)")
            self.rejection_reason = reason
        else:
            self.rejection_reason = None
        return self


class SavingsAccountDetailsOut(BaseModel):
    id: int
    account_number: str
    savings_scheme_id: int
    scheme_name: str
    scheme_code: str
    branch_id: int
    branch_name: str
    branch_code: str
    ifsc_code: str | None
    balance: Decimal
    status: str
    opened_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberSavingsAccountOpeningRequestOut(BaseModel):
    id: int
    savings_scheme_id: int
    scheme_name: str
    scheme_code: str
    status: str
    rejection_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    account: SavingsAccountDetailsOut | None = None


class BranchAdminSavingsAccountOpeningRequestOut(MemberSavingsAccountOpeningRequestOut):
    member_id: int
    member_code: str | None
    member_name: str
    member_email: str
    member_mobile: str | None
    member_kyc_status: str
    nominee_status: str


class SavingsAccountAdminOut(SavingsAccountDetailsOut):
    member_id: int
    member_code: str | None
    member_name: str
    member_email: str
    member_mobile: str | None
    member_kyc_status: str
    nominee_status: str
    branch_city: str
    branch_state: str
    branch_address: str
    branch_contact_number: str
    opening_request_id: int
    opening_request_status: str
    request_created_at: datetime
    reviewed_at: datetime | None
    reviewed_by_name: str | None
