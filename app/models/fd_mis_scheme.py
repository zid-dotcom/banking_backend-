from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String, text

from app.core.database import Base


class FdMisScheme(Base):
    __tablename__ = "fd_mis_schemes"
    __table_args__ = (
        Index(
            "uq_fd_mis_schemes_code_not_deleted",
            "scheme_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column(String(100), nullable=False)
    scheme_code = Column(String(20), nullable=False)
    minimum_fd_mis_amount = Column(Numeric(14, 2), nullable=False)
    fd_mis_lock_in_period_months = Column(Integer, nullable=False)
    annual_interest_rate = Column(Numeric(7, 3), nullable=False)
    senior_citizen_addon_interest_rate = Column(Numeric(7, 3), nullable=False, default=0)
    interest_lock_in_period_months = Column(Integer, nullable=False)
    tenure_value = Column(Integer, nullable=False)
    tenure_unit = Column(String(10), nullable=False)
    bonus_rate = Column(Numeric(12, 2), nullable=False, default=0)
    bonus_rate_type = Column(String(10), nullable=False, default="percent")
    cancellation_charges = Column(Numeric(12, 2), nullable=False, default=0)
    cancellation_charges_type = Column(String(10), nullable=False, default="fixed")
    penal_charges_percent = Column(Numeric(7, 3), nullable=False, default=0)
    stationary_charges = Column(Numeric(12, 2), nullable=False, default=0)
    interest_payout_type = Column(String(30), nullable=False)
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
