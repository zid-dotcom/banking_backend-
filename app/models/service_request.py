from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        Index("ix_service_requests_branch_status", "branch_id", "status"),
        Index("ix_service_requests_member_created", "member_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    subject = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    branch = relationship("Branch")
    member = relationship("User", foreign_keys=[member_id])
    replies = relationship(
        "ServiceRequestReply",
        back_populates="service_request",
        order_by="ServiceRequestReply.created_at",
        cascade="all, delete-orphan",
    )


class ServiceRequestReply(Base):
    __tablename__ = "service_request_replies"
    __table_args__ = (
        Index("ix_service_request_replies_request_created", "service_request_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(
        Integer, ForeignKey("service_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    edited_at = Column(DateTime(timezone=True), nullable=True)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    service_request = relationship("ServiceRequest", back_populates="replies")
    sender = relationship("User", foreign_keys=[sender_id])
    edited_by = relationship("User", foreign_keys=[edited_by_id])
