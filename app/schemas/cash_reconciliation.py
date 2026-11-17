from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashDayOpeningIn(BaseModel):
    business_date: date
    opening_cash: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class CashDayClosingIn(BaseModel):
    closing_cash: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class CashReconciliationReviewIn(BaseModel):
    explanation: str | None = Field(default=None, max_length=1000)


class CashReconciliationTransactionOut(BaseModel):
    id: int
    receipt_number: str
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    notes: str | None
    created_at: datetime


class CashReconciliationOut(BaseModel):
    id: int
    business_date: date
    branch_id: int
    cashier_user_id: int
    cashier_code: str | None
    cashier_name: str
    opening_cash: Decimal
    closing_cash: Decimal | None
    deposit_total: Decimal
    withdrawal_total: Decimal
    expected_closing_cash: Decimal | None
    difference: Decimal | None
    status: str
    accountant_user_id: int | None
    accountant_name: str | None
    accountant_explanation: str | None
    opened_at: datetime
    closed_at: datetime | None
    reviewed_at: datetime | None


class CashReconciliationDetailsOut(CashReconciliationOut):
    transactions: list[CashReconciliationTransactionOut]


class BranchDailyCashReportOut(BaseModel):
    business_date: date
    branch_id: int
    branch_name: str
    cashier_count: int
    open_cashier_count: int
    pending_accountant_review_count: int
    total_opening_cash: Decimal
    total_deposits: Decimal
    total_withdrawals: Decimal
    total_expected_closing_cash: Decimal
    total_counted_closing_cash: Decimal
    total_difference: Decimal
    cashier_reports: list[CashReconciliationOut]
