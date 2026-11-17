from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import AnnouncementOut

router = APIRouter(
    prefix="/branch-admin/announcements",
    tags=["Branch Admin - Announcements"],
)


@router.get("", response_model=List[AnnouncementOut])
def list_announcements_for_branch_admin(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = db.query(Announcement).filter(
        Announcement.is_active == True,
        Announcement.is_deleted == False,
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            Announcement.title.ilike(like) | Announcement.message.ilike(like)
        )
    return query.order_by(Announcement.created_at.desc(), Announcement.id.desc()).offset(skip).limit(limit).all()
