import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TenureMonths = Literal[1, 3, 6, 9, 12, 18, 24, 36, 48, 60, 72, 84, 96, 108, 120, 180]
ChargeType = Literal["percent", "fixed"]
InterestType = Literal["reducing_emi", "flat_emi", "flat_advanced_interest_deduction"]
PerEmiChargeType = Literal["on_emi", "on_principal"]

CHARGE_FIELDS = (
    ("processing_fee", "processing_fee_type"),
    ("stamp_duty_charge", "stamp_duty_charge_type"),
    ("insurance_fee", "insurance_fee_type"),
    ("documentation_fee", "documentation_fee_type"),
    ("foreclosure_charges", "foreclosure_charges_type"),
    ("penalty_charges", "penalty_charges_type"),
    ("sms_charges", "sms_charges_type"),
    ("fuel_charges", "fuel_charges_type"),
    ("stationary_charges", "stationary_charges_type"),
    ("maintenance_charges", "maintenance_charges_type"),
    ("collection_charges", "collection_charges_type"),
)


class LoanSchemeFields(BaseModel):
    scheme_name: str = Field(min_length=2, max_length=100)
    scheme_code: str = Field(min_length=2, max_length=20)
    max_loan_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    max_tenure_months: TenureMonths
    annual_interest_rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=3)
    overdue_interest_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=7, decimal_places=3)

    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    processing_fee_type: ChargeType = "percent"
    stamp_duty_charge: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    stamp_duty_charge_type: ChargeType = "percent"
    insurance_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    insurance_fee_type: ChargeType = "percent"
    documentation_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    documentation_fee_type: ChargeType = "percent"
    foreclosure_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    foreclosure_charges_type: ChargeType = "percent"
    credit_period_days: int = Field(default=0, ge=0, le=365)
    penalty_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    penalty_charges_type: ChargeType = "percent"

    interest_type: InterestType
    is_active: bool = True

    sms_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    sms_charges_type: ChargeType = "fixed"
    fuel_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    fuel_charges_type: ChargeType = "fixed"
    stationary_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    stationary_charges_type: ChargeType = "fixed"
    maintenance_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    maintenance_charges_type: ChargeType = "fixed"
    collection_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    collection_charges_type: ChargeType = "fixed"
    per_emi_charge_type: PerEmiChargeType = "on_emi"

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
    def validate_percentage_charges(self):
        for value_field, type_field in CHARGE_FIELDS:
            if getattr(self, type_field) == "percent" and getattr(self, value_field) > 100:
                raise ValueError(f"{value_field} cannot exceed 100 when its type is percent")
        return self


class LoanSchemeCreate(LoanSchemeFields):
    pass


class LoanSchemeUpdate(LoanSchemeFields):
    pass


class LoanSchemeOut(LoanSchemeFields):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoanSchemeStatusUpdate(BaseModel):
    is_active: bool
