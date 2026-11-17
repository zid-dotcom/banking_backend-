from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashTransactionCreate(BaseModel):
    account_number: str = Field(pattern=r"^\d{16}$")
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)


class CashDepositCreate(CashTransactionCreate):
    pass


class CashWithdrawalCreate(CashTransactionCreate):
    pass


class CashierAccountLookupOut(BaseModel):
    account_id: int
    account_number: str
    member_code: str | None
    member_name: str
    scheme_name: str
    status: str
    balance: Decimal
    lock_in_amount: Decimal
    withdrawable_balance: Decimal
    branch_name: str
    can_accept_deposit: bool
    can_withdraw: bool


class CashTransactionOut(BaseModel):
    id: int
    receipt_number: str
    account_id: int
    account_number: str
    member_code: str | None
    member_name: str
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    branch_id: int
    branch_name: str
    branch_code: str
    ifsc_code: str | None
    cashier_user_id: int
    cashier_code: str | None
    cashier_name: str
    notes: str | None
    created_at: datetime


class CashDepositOut(CashTransactionOut):
    account_status: str
    minimum_opening_balance: Decimal
    remaining_opening_deposit: Decimal
    message: str
