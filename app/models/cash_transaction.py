from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text

from app.core.database import Base


class CashTransaction(Base):
    __tablename__ = "cash_transactions"
    __table_args__ = (
        Index("ix_cash_transactions_branch_created", "branch_id", "created_at"),
        Index("ix_cash_transactions_staff_created", "staff_user_id", "created_at"),
        Index("ix_cash_transactions_account_created", "account_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(12), nullable=False, unique=True)
    account_id = Column(Integer, ForeignKey("savings_accounts.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    staff_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    balance_before = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
