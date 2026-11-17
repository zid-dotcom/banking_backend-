from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnnouncementFields(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    message: str = Field(min_length=1, max_length=10000)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Announcement title must contain at least 2 characters")
        return value

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Announcement message cannot be empty")
        return value


class AnnouncementCreate(AnnouncementFields):
    pass


class AnnouncementUpdate(AnnouncementFields):
    pass


class AnnouncementOut(BaseModel):
    id: int
    title: str
    message: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementStatusUpdate(BaseModel):
    is_active: bool
