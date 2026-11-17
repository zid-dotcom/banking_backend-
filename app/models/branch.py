from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Index, Integer, String

from app.core.database import Base


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (Index("uq_branches_ifsc_code", "ifsc_code", unique=True),)

    id = Column(Integer, primary_key=True, index=True)
    branch_code = Column(String(6), unique=True, index=True, nullable=False)
    ifsc_code = Column(String(11), nullable=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    contact_number = Column(String(15), nullable=False)
    opening_date = Column(Date, default=date.today)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))