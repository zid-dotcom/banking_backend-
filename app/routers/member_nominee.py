from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.core.uploads import delete_nominee_files, read_image, save_nominee_files
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.nominee_change_request import NomineeChangeRequest
from app.models.user import User
from app.schemas.nominee import NomineeCreate, NomineeOut

router = APIRouter(prefix="/member/nominee", tags=["Member - Nominee"])


def get_own_member(db: Session, user: User) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Member profile not found")
    return member


@router.post("", response_model=NomineeOut, status_code=status.HTTP_201_CREATED)
def submit_nominee(
    nominee_name: str = Form(...),
    relationship_type: str = Form(...),
    date_of_birth: date = Form(...),
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    try:
        data = NomineeCreate(
            nominee_name=nominee_name,
            relationship_type=relationship_type,
            date_of_birth=date_of_birth,
        )
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            e.errors(include_url=False, include_context=False, include_input=False),
        )

    member = get_own_member(db, current_user)

    nominee = db.query(Nominee).filter(Nominee.member_id == member.id).first()
    approved_change_request = None
    if nominee and nominee.status == "approved":
        approved_change_request = (
            db.query(NomineeChangeRequest)
            .filter(
                NomineeChangeRequest.member_id == member.id,
                NomineeChangeRequest.status == "approved",
                NomineeChangeRequest.consumed_at.is_(None),
            )
            .order_by(NomineeChangeRequest.created_at.desc(), NomineeChangeRequest.id.desc())
            .with_for_update()
            .first()
        )
        if not approved_change_request:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Request and receive branch approval before changing an approved nominee",
            )
    elif nominee and nominee.status != "rejected":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Nominee already {nominee.status}")

    images = {
        "nominee_aadhaar_front": read_image(aadhaar_front, "Nominee Aadhaar front image"),
        "nominee_aadhaar_back": read_image(aadhaar_back, "Nominee Aadhaar back image"),
    }

    try:
        delete_nominee_files(current_user.user_code)
        paths = save_nominee_files(current_user.user_code, images)

        if nominee is None:
            nominee = Nominee(member_id=member.id)
            db.add(nominee)

        nominee.nominee_name = data.nominee_name
        nominee.relationship_type = data.relationship_type
        nominee.date_of_birth = data.date_of_birth
        nominee.aadhaar_front_path = paths["nominee_aadhaar_front"]
        nominee.aadhaar_back_path = paths["nominee_aadhaar_back"]
        nominee.status = "pending"
        nominee.rejection_reason = None
        nominee.reviewed_by = None
        nominee.reviewed_at = None
        nominee.submitted_at = datetime.now(timezone.utc)
        if approved_change_request:
            approved_change_request.consumed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(nominee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Nominee already submitted")
    except Exception:
        db.rollback()
        raise

    return nominee


@router.get("", response_model=NomineeOut)
def get_my_nominee(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("member")),
):
    member = get_own_member(db, current_user)
    nominee = db.query(Nominee).filter(Nominee.member_id == member.id).first()
    if not nominee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No nominee submitted yet")
    return nominee