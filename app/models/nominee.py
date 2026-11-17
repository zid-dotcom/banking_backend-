from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from app.core.database import Base
from app.models.member import Member  # noqa: F401


class Nominee(Base):
    __tablename__ = "nominees"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, nullable=False, index=True)

    nominee_name = Column(String(100), nullable=False)
    relationship_type = Column(String(30), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    aadhaar_front_path = Column(String(255), nullable=False)
    aadhaar_back_path = Column(String(255), nullable=False)

    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    rejection_reason = Column(String(255), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))