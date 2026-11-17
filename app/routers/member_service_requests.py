from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.branch import Branch
from app.models.service_request import ServiceRequest, ServiceRequestReply
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestDetailOut,
    ServiceRequestListOut,
)

router = APIRouter(prefix="/member", tags=["Member - Service Requests"])


@router.post(
    "/service-requests",
    response_model=ServiceRequestDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_service_request(
    data: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    if current_user.branch_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not assigned to a branch")

    branch = db.query(Branch).filter(
        Branch.id == current_user.branch_id,
        Branch.is_active == True,
        Branch.is_deleted == False,
    ).first()
    if not branch:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your assigned branch is unavailable")

    service_request = ServiceRequest(
        member_id=current_user.id,
        branch_id=branch.id,
        subject=data.subject,
        message=data.message,
        status="pending",
    )
    db.add(service_request)
    db.commit()
    db.refresh(service_request)
    return service_request


@router.get("/service-requests", response_model=List[ServiceRequestListOut])
def list_my_service_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    request_status: str | None = Query(default=None, alias="status", pattern="^(pending|in_progress|solved)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    query = (
        db.query(ServiceRequest)
        .options(joinedload(ServiceRequest.branch), joinedload(ServiceRequest.member))
        .filter(ServiceRequest.member_id == current_user.id)
    )
    if request_status is not None:
        query = query.filter(ServiceRequest.status == request_status)
    return query.order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc()).offset(skip).limit(limit).all()


@router.get("/service-requests/{request_id}", response_model=ServiceRequestDetailOut)
def get_my_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    service_request = (
        db.query(ServiceRequest)
        .options(
            joinedload(ServiceRequest.branch),
            joinedload(ServiceRequest.member),
            selectinload(ServiceRequest.replies).joinedload(ServiceRequestReply.sender),
        )
        .filter(
            ServiceRequest.id == request_id,
            ServiceRequest.member_id == current_user.id,
        )
        .first()
    )
    if not service_request:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    return service_request
