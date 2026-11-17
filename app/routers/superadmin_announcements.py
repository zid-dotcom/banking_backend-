from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementStatusUpdate,
    AnnouncementUpdate,
)

router = APIRouter(prefix="/superadmin/announcements", tags=["Superadmin - Announcements"])


def get_announcement_or_404(db: Session, announcement_id: int) -> Announcement:
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.is_deleted == False,
    ).first()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return announcement


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    announcement = Announcement(**data.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("", response_model=List[AnnouncementOut])
def list_announcements(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    query = db.query(Announcement).filter(Announcement.is_deleted == False)
    if is_active is not None:
        query = query.filter(Announcement.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            Announcement.title.ilike(like) | Announcement.message.ilike(like)
        )
    return query.order_by(Announcement.created_at.desc(), Announcement.id.desc()).offset(skip).limit(limit).all()


@router.get("/{announcement_id}", response_model=AnnouncementOut)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    return get_announcement_or_404(db, announcement_id)


@router.put("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    announcement = get_announcement_or_404(db, announcement_id)
    for field, value in data.model_dump().items():
        setattr(announcement, field, value)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.patch("/{announcement_id}/status", response_model=AnnouncementOut)
def change_announcement_status(
    announcement_id: int,
    data: AnnouncementStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    announcement = get_announcement_or_404(db, announcement_id)
    announcement.is_active = data.is_active
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("superadmin")),
):
    announcement = get_announcement_or_404(db, announcement_id)
    announcement.is_deleted = True
    announcement.deleted_at = datetime.now(timezone.utc)
    announcement.is_active = False
    db.commit()
    return {"message": "Announcement deleted", "id": announcement.id}
