from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.emergency_case import EmergencyCase, EmergencyCaseMessage
from app.models.user import User
from app.schemas.emergency_case import (
    BranchAdminEmergencyUnreadCountOut,
    EmergencyCaseCreate,
    EmergencyCaseDetailOut,
    EmergencyCaseListOut,
    EmergencyMessageCreate,
)

router = APIRouter(
    prefix="/branch-admin/emergency-cases",
    tags=["Branch Admin - Emergency Cases"],
)


def _get_case_or_404(db: Session, case_id: int, user: User) -> EmergencyCase:
    case = (
        db.query(EmergencyCase)
        .options(
            joinedload(EmergencyCase.branch),
            joinedload(EmergencyCase.created_by),
            selectinload(EmergencyCase.messages).joinedload(EmergencyCaseMessage.sender),
        )
        .filter(
            EmergencyCase.id == case_id,
            EmergencyCase.branch_id == user.branch_id,
            EmergencyCase.created_by_id == user.id,
        )
        .first()
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency case not found")

    changed = False
    for message in case.messages:
        if message.sender.role == "superadmin" and message.read_at is None:
            message.read_at = datetime.now(timezone.utc)
            changed = True
    if changed:
        db.commit()
    return case


def _unread_counts_by_case(db: Session, case_ids: list[int]) -> dict[int, int]:
    if not case_ids:
        return {}
    rows = (
        db.query(EmergencyCaseMessage.case_id, func.count(EmergencyCaseMessage.id))
        .join(User, EmergencyCaseMessage.sender_id == User.id)
        .filter(
            EmergencyCaseMessage.case_id.in_(case_ids),
            EmergencyCaseMessage.read_at.is_(None),
            User.role == "superadmin",
        )
        .group_by(EmergencyCaseMessage.case_id)
        .all()
    )
    return {case_id: count for case_id, count in rows}


def _case_list_item(case: EmergencyCase, unread_count: int) -> dict:
    return {
        "id": case.id,
        "subject": case.subject,
        "branch": case.branch,
        "created_by": case.created_by,
        "unread_count": unread_count,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


@router.post("", response_model=EmergencyCaseDetailOut, status_code=status.HTTP_201_CREATED)
def create_emergency_case(
    data: EmergencyCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    if current_user.branch_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is not assigned to a branch")

    case = EmergencyCase(
        branch_id=current_user.branch_id,
        created_by_id=current_user.id,
        subject=data.subject,
    )
    db.add(case)
    db.flush()
    db.add(EmergencyCaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=data.message,
    ))
    db.commit()
    return get_branch_admin_emergency_case(case.id, db, current_user)


@router.get("/unread-count", response_model=BranchAdminEmergencyUnreadCountOut)
def get_branch_admin_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    count = (
        db.query(func.count(EmergencyCaseMessage.id))
        .join(EmergencyCase, EmergencyCaseMessage.case_id == EmergencyCase.id)
        .join(User, EmergencyCaseMessage.sender_id == User.id)
        .filter(
            EmergencyCase.created_by_id == current_user.id,
            EmergencyCase.branch_id == current_user.branch_id,
            EmergencyCaseMessage.read_at.is_(None),
            User.role == "superadmin",
        )
        .scalar()
    )
    return {"unread_count": count or 0}


@router.get("", response_model=List[EmergencyCaseListOut])
def list_branch_admin_emergency_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        db.query(EmergencyCase)
        .options(joinedload(EmergencyCase.branch), joinedload(EmergencyCase.created_by))
        .join(Branch, EmergencyCase.branch_id == Branch.id)
        .filter(
            EmergencyCase.branch_id == current_user.branch_id,
            EmergencyCase.created_by_id == current_user.id,
        )
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            EmergencyCase.subject.ilike(like)
            | Branch.name.ilike(like)
            | Branch.branch_code.ilike(like)
            | Branch.city.ilike(like)
        )
    cases = query.order_by(EmergencyCase.updated_at.desc(), EmergencyCase.id.desc()).offset(skip).limit(limit).all()
    counts = _unread_counts_by_case(db, [case.id for case in cases])
    return [_case_list_item(case, counts.get(case.id, 0)) for case in cases]


@router.get("/{case_id}", response_model=EmergencyCaseDetailOut)
def get_branch_admin_emergency_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    case = _get_case_or_404(db, case_id, current_user)
    unread_count = _unread_counts_by_case(db, [case.id]).get(case.id, 0)
    return {**_case_list_item(case, unread_count), "messages": case.messages}


@router.post("/{case_id}/messages", response_model=EmergencyCaseDetailOut)
def send_branch_admin_emergency_message(
    case_id: int,
    data: EmergencyMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    case = _get_case_or_404(db, case_id, current_user)
    db.add(EmergencyCaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=data.message,
    ))
    case.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_branch_admin_emergency_case(case_id, db, current_user)
