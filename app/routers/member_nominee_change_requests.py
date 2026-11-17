from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.nominee_change_request import NomineeChangeRequest
from app.models.user import User
from app.schemas.nominee_change_request import (
    NomineeChangeRequestCreate,
    NomineeChangeRequestOut,
)

router = APIRouter(
    prefix="/member/nominee-change-requests",
    tags=["Member - Nominee Change Requests"],
)


@router.post("", response_model=NomineeChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_nominee_change_request(
    data: NomineeChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")

    nominee = db.query(Nominee).filter(Nominee.member_id == member.id).first()
    if not nominee or nominee.status != "approved":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A nominee must be approved before requesting a change",
        )

    outstanding_request = db.query(NomineeChangeRequest).filter(
        NomineeChangeRequest.member_id == member.id,
        (
            (NomineeChangeRequest.status == "pending")
            | (
                (NomineeChangeRequest.status == "approved")
                & NomineeChangeRequest.consumed_at.is_(None)
            )
        ),
    ).first()
    if outstanding_request:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A nominee change request is already awaiting review or resubmission",
        )

    change_request = NomineeChangeRequest(
        member_id=member.id,
        subject=data.subject,
        message=data.message,
        status="pending",
    )
    db.add(change_request)
    db.commit()
    db.refresh(change_request)
    return change_request


@router.get("", response_model=List[NomineeChangeRequestOut])
def list_my_nominee_change_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")
    return (
        db.query(NomineeChangeRequest)
        .filter(NomineeChangeRequest.member_id == member.id)
        .order_by(NomineeChangeRequest.created_at.desc(), NomineeChangeRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{request_id}", response_model=NomineeChangeRequestOut)
def get_my_nominee_change_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    member = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member profile not found")
    change_request = db.query(NomineeChangeRequest).filter(
        NomineeChangeRequest.id == request_id,
        NomineeChangeRequest.member_id == member.id,
    ).first()
    if not change_request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nominee change request not found")
    return change_request
