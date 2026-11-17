import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ChargeFrequency = Literal["monthly", "quarterly", "half_yearly", "yearly"]
InterestPayoutType = Literal["monthly", "quarterly", "half_yearly", "yearly"]


class SavingsSchemeFields(BaseModel):
    scheme_name: str = Field(min_length=2, max_length=100)
    scheme_code: str = Field(min_length=2, max_length=20)
    min_opening_balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    min_monthly_avg_balance: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    annual_interest_rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=3)
    senior_citizen_addon_interest_rate: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=3
    )
    interest_payout_type: InterestPayoutType
    lock_in_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    min_monthly_avg_balance_charge: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    service_charge_frequency: ChargeFrequency = "monthly"
    service_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    sms_charge_frequency: ChargeFrequency = "monthly"
    sms_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
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
    def validate_interest_rates(self):
        if self.annual_interest_rate + self.senior_citizen_addon_interest_rate > 100:
            raise ValueError("Combined annual and senior citizen interest rates cannot exceed 100")
        return self


class SavingsSchemeCreate(SavingsSchemeFields):
    pass


class SavingsSchemeUpdate(SavingsSchemeFields):
    pass


class SavingsSchemeOut(SavingsSchemeFields):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavingsSchemeStatusUpdate(BaseModel):
    is_active: bool
