from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String, text

from app.core.database import Base


class LoanScheme(Base):
    __tablename__ = "loan_schemes"
    __table_args__ = (
        Index(
            "uq_loan_schemes_active_code",
            "scheme_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column(String(100), nullable=False)
    scheme_code = Column(String(20), nullable=False)
    max_loan_amount = Column(Numeric(14, 2), nullable=False)
    max_tenure_months = Column(Integer, nullable=False)
    annual_interest_rate = Column(Numeric(7, 3), nullable=False)
    overdue_interest_rate = Column(Numeric(7, 3), nullable=False, default=0)

    processing_fee = Column(Numeric(12, 2), nullable=False, default=0)
    processing_fee_type = Column(String(10), nullable=False, default="percent")
    stamp_duty_charge = Column(Numeric(12, 2), nullable=False, default=0)
    stamp_duty_charge_type = Column(String(10), nullable=False, default="percent")
    insurance_fee = Column(Numeric(12, 2), nullable=False, default=0)
    insurance_fee_type = Column(String(10), nullable=False, default="percent")
    documentation_fee = Column(Numeric(12, 2), nullable=False, default=0)
    documentation_fee_type = Column(String(10), nullable=False, default="percent")
    foreclosure_charges = Column(Numeric(12, 2), nullable=False, default=0)
    foreclosure_charges_type = Column(String(10), nullable=False, default="percent")
    credit_period_days = Column(Integer, nullable=False, default=0)
    penalty_charges = Column(Numeric(12, 2), nullable=False, default=0)
    penalty_charges_type = Column(String(10), nullable=False, default="percent")

    interest_type = Column(String(40), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    sms_charges = Column(Numeric(12, 2), nullable=False, default=0)
    sms_charges_type = Column(String(10), nullable=False, default="fixed")
    fuel_charges = Column(Numeric(12, 2), nullable=False, default=0)
    fuel_charges_type = Column(String(10), nullable=False, default="fixed")
    stationary_charges = Column(Numeric(12, 2), nullable=False, default=0)
    stationary_charges_type = Column(String(10), nullable=False, default="fixed")
    maintenance_charges = Column(Numeric(12, 2), nullable=False, default=0)
    maintenance_charges_type = Column(String(10), nullable=False, default="fixed")
    collection_charges = Column(Numeric(12, 2), nullable=False, default=0)
    collection_charges_type = Column(String(10), nullable=False, default="fixed")
    per_emi_charge_type = Column(String(20), nullable=False, default="on_emi")

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
