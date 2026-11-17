from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from app.core.database import Base
from app.models.user import User  # noqa: F401


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    country = Column(String(50), nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    street = Column(String(150), nullable=False)
    building_no = Column(String(50), nullable=False)
    zip_code = Column(String(10), nullable=False)

    aadhaar_number = Column(String(12), unique=True, nullable=False)
    pan_number = Column(String(10), unique=True, nullable=False)

    bank_holder_name = Column(String(100), nullable=False)
    bank_account_number = Column(String(18), nullable=False)
    ifsc_code = Column(String(11), nullable=False)

    aadhaar_front_path = Column(String(255), nullable=False)
    aadhaar_back_path = Column(String(255), nullable=False)
    pan_image_path = Column(String(255), nullable=False)
    passbook_image_path = Column(String(255), nullable=False)

    status = Column(String(20), nullable=False, default="pending")
    rejection_reason = Column(String(255), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))