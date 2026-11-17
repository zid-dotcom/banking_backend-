from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.notifications import add_member_notification
from app.core.security import require_roles
from app.models.service_request import ServiceRequest, ServiceRequestReply
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestDetailOut,
    ServiceRequestListOut,
    ServiceRequestReplyCreate,
    ServiceRequestStatusUpdate,
)

router = APIRouter(
    prefix="/branch-admin/service-requests",
    tags=["Branch Admin - Service Requests"],
)


def get_branch_request_or_404(db: Session, request_id: int, branch_id: int) -> ServiceRequest:
    request = db.query(ServiceRequest).filter(
        ServiceRequest.id == request_id,
        ServiceRequest.branch_id == branch_id,
    ).first()
    if not request:
        raise HTTPException(status_code=404, detail="Service request not found")
    return request


@router.get("", response_model=List[ServiceRequestListOut])
def list_branch_service_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    request_status: str | None = Query(default=None, alias="status", pattern="^(pending|in_progress|solved)$"),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    query = (
        db.query(ServiceRequest)
        .options(joinedload(ServiceRequest.branch), joinedload(ServiceRequest.member))
        .filter(ServiceRequest.branch_id == current_user.branch_id)
    )
    if request_status is not None:
        query = query.filter(ServiceRequest.status == request_status)
    if search:
        like = f"%{search.strip()}%"
        query = query.join(ServiceRequest.member).filter(
            ServiceRequest.subject.ilike(like)
            | ServiceRequest.message.ilike(like)
            | User.full_name.ilike(like)
            | User.user_code.ilike(like)
        )
    return query.order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc()).offset(skip).limit(limit).all()


@router.get("/{request_id}", response_model=ServiceRequestDetailOut)
def get_branch_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    service_request = (
        db.query(ServiceRequest)
        .options(
            joinedload(ServiceRequest.branch),
            joinedload(ServiceRequest.member),
            selectinload(ServiceRequest.replies).joinedload(ServiceRequestReply.sender),
            selectinload(ServiceRequest.replies).joinedload(ServiceRequestReply.edited_by),
        )
        .filter(
            ServiceRequest.id == request_id,
            ServiceRequest.branch_id == current_user.branch_id,
        )
        .first()
    )
    if not service_request:
        raise HTTPException(status_code=404, detail="Service request not found")
    return service_request


@router.post("/{request_id}/replies", response_model=ServiceRequestDetailOut)
def reply_to_service_request(
    request_id: int,
    data: ServiceRequestReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    service_request = get_branch_request_or_404(db, request_id, current_user.branch_id)
    db.add(ServiceRequestReply(
        service_request_id=service_request.id,
        sender_id=current_user.id,
        message=data.message,
    ))
    add_member_notification(
        db,
        recipient_id=service_request.member_id,
        service_request_id=service_request.id,
        notification_type="service_request_reply",
        title="New reply to your service request",
        message=(
            f"A branch administrator replied to your request "
            f"'{service_request.subject}': {data.message}"
        ),
    )
    db.commit()
    return get_branch_service_request(request_id, db, current_user)


@router.patch("/{request_id}/replies/{reply_id}", response_model=ServiceRequestDetailOut)
def edit_branch_service_request_reply(
    request_id: int,
    reply_id: int,
    data: ServiceRequestReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    service_request = get_branch_request_or_404(db, request_id, current_user.branch_id)
    reply = db.query(ServiceRequestReply).filter(
        ServiceRequestReply.id == reply_id,
        ServiceRequestReply.service_request_id == service_request.id,
    ).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    reply.message = data.message
    reply.edited_at = datetime.now(timezone.utc)
    reply.edited_by_id = current_user.id
    db.commit()
    return get_branch_service_request(request_id, db, current_user)


@router.patch("/{request_id}/status", response_model=ServiceRequestDetailOut)
def update_branch_service_request_status(
    request_id: int,
    data: ServiceRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("branch_admin")),
):
    service_request = get_branch_request_or_404(db, request_id, current_user.branch_id)
    previous_status = service_request.status
    service_request.status = data.status
    if previous_status != data.status:
        add_member_notification(
            db,
            recipient_id=service_request.member_id,
            service_request_id=service_request.id,
            notification_type="service_request_status",
            title="Service request status updated",
            message=f"Your request '{service_request.subject}' is now {data.status.replace('_', ' ')}.",
        )
    db.commit()
    return get_branch_service_request(request_id, db, current_user)
