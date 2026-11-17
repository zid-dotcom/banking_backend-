from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class EmergencyCase(Base):
    __tablename__ = "emergency_cases"
    __table_args__ = (
        Index("ix_emergency_cases_branch_updated", "branch_id", "updated_at"),
        Index("ix_emergency_cases_creator_updated", "created_by_id", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    branch = relationship("Branch")
    created_by = relationship("User", foreign_keys=[created_by_id])
    messages = relationship(
        "EmergencyCaseMessage",
        back_populates="emergency_case",
        order_by="EmergencyCaseMessage.created_at",
        cascade="all, delete-orphan",
    )


class EmergencyCaseMessage(Base):
    __tablename__ = "emergency_case_messages"
    __table_args__ = (
        Index("ix_emergency_case_messages_case_created", "case_id", "created_at"),
        Index("ix_emergency_case_messages_read_created", "read_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer, ForeignKey("emergency_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    emergency_case = relationship("EmergencyCase", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
