from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import relationship

from app.core.database import Base


class SavingsAccountOpeningRequest(Base):
    __tablename__ = "savings_account_opening_requests"
    __table_args__ = (
        Index("ix_savings_account_opening_requests_branch_status", "branch_id", "status"),
        Index("ix_savings_account_opening_requests_member_created", "member_id", "created_at"),
        Index(
            "uq_savings_account_opening_pending_member_scheme",
            "member_id",
            "savings_scheme_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    savings_scheme_id = Column(Integer, ForeignKey("savings_schemes.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    rejection_reason = Column(String(255), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    member = relationship("User", foreign_keys=[member_id])
    branch = relationship("Branch")
    scheme = relationship("SavingsScheme")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    account = relationship("SavingsAccount", back_populates="opening_request", uselist=False)


class SavingsAccount(Base):
    __tablename__ = "savings_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(16), nullable=False, unique=True)
    opening_request_id = Column(
        Integer,
        ForeignKey("savings_account_opening_requests.id"),
        nullable=False,
        unique=True,
    )
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    savings_scheme_id = Column(Integer, ForeignKey("savings_schemes.id"), nullable=False, index=True)
    balance = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    status = Column(String(30), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    opening_request = relationship("SavingsAccountOpeningRequest", back_populates="account")
    member = relationship("User", foreign_keys=[member_id])
    branch = relationship("Branch")
    scheme = relationship("SavingsScheme")
