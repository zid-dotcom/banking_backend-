from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String, text

from app.core.database import Base


class SavingsScheme(Base):
    __tablename__ = "savings_schemes"
    __table_args__ = (
        Index(
            "uq_savings_schemes_code_not_deleted",
            "scheme_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column(String(100), nullable=False)
    scheme_code = Column(String(20), nullable=False)
    min_opening_balance = Column(Numeric(14, 2), nullable=False)
    min_monthly_avg_balance = Column(Numeric(14, 2), nullable=False)
    annual_interest_rate = Column(Numeric(7, 3), nullable=False)
    senior_citizen_addon_interest_rate = Column(Numeric(7, 3), nullable=False, default=0)
    interest_payout_type = Column(String(20), nullable=False)
    lock_in_amount = Column(Numeric(14, 2), nullable=False, default=0)
    min_monthly_avg_balance_charge = Column(Numeric(12, 2), nullable=False, default=0)
    service_charge_frequency = Column(String(20), nullable=False, default="monthly")
    service_charges = Column(Numeric(12, 2), nullable=False, default=0)
    sms_charge_frequency = Column(String(20), nullable=False, default="monthly")
    sms_charges = Column(Numeric(12, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
