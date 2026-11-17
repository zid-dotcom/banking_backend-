import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ChargeType = Literal["percent", "fixed"]
TenureUnit = Literal["months", "years"]
InterestPayoutType = Literal[
    "cumulative_yearly",
    "cumulative_half_yearly",
    "cumulative_quarterly",
    "cumulative_monthly",
    "yearly",
    "half_yearly",
    "quarterly",
    "monthly",
]


class FdMisSchemeFields(BaseModel):
    scheme_name: str = Field(min_length=2, max_length=100)
    scheme_code: str = Field(min_length=2, max_length=20)
    minimum_fd_mis_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    fd_mis_lock_in_period_months: int = Field(ge=0, le=1200)
    annual_interest_rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=3)
    senior_citizen_addon_interest_rate: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=3
    )
    interest_lock_in_period_months: int = Field(ge=0, le=1200)
    tenure_value: int = Field(ge=1, le=1200)
    tenure_unit: TenureUnit
    bonus_rate: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    bonus_rate_type: ChargeType = "percent"
    cancellation_charges: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    cancellation_charges_type: ChargeType = "fixed"
    penal_charges_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=3
    )
    stationary_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    interest_payout_type: InterestPayoutType
    is_active: bool = True

    @field_validator("scheme_name")
    @classmethod
    def normalize_scheme_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Scheme name must contain at least 2 characters")
        return value

    @field_validator("scheme_code")
    @classmethod
    def normalize_scheme_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,19}", value):
            raise ValueError("Scheme code must use 2-20 letters, numbers, hyphens, or underscores")
        return value

    @model_validator(mode="after")
    def validate_scheme_rates(self):
        if self.annual_interest_rate + self.senior_citizen_addon_interest_rate > 100:
            raise ValueError("Combined annual and senior citizen interest rates cannot exceed 100")
        if self.bonus_rate_type == "percent" and self.bonus_rate > 100:
            raise ValueError("Bonus rate cannot exceed 100 when its type is percent")
        if self.cancellation_charges_type == "percent" and self.cancellation_charges > 100:
            raise ValueError("Cancellation charges cannot exceed 100 when its type is percent")
        return self


class FdMisSchemeCreate(FdMisSchemeFields):
    pass


class FdMisSchemeUpdate(FdMisSchemeFields):
    pass


class FdMisSchemeOut(FdMisSchemeFields):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FdMisSchemeStatusUpdate(BaseModel):
    is_active: bool
