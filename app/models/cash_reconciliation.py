from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)

from app.core.database import Base


class CashReconciliation(Base):
    __tablename__ = "cash_reconciliations"
    __table_args__ = (
        UniqueConstraint(
            "cashier_user_id",
            "business_date",
            name="uq_cash_reconciliations_cashier_date",
        ),
        Index("ix_cash_reconciliations_branch_date", "branch_id", "business_date"),
        Index("ix_cash_reconciliations_cashier_date", "cashier_user_id", "business_date"),
        Index(
            "uq_cash_reconciliations_one_open_per_cashier",
            "cashier_user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    cashier_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    business_date = Column(Date, nullable=False)
    opening_cash = Column(Numeric(14, 2), nullable=False)
    closing_cash = Column(Numeric(14, 2), nullable=True)
    deposit_total = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    withdrawal_total = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    expected_closing_cash = Column(Numeric(14, 2), nullable=True)
    difference = Column(Numeric(14, 2), nullable=True)
    status = Column(String(20), nullable=False, default="open")
    accountant_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accountant_explanation = Column(Text, nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
