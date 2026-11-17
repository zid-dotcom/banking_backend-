from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_login
from app.core.uploads import delete_member_files, read_image, save_member_files
from app.models.branch import Branch
from app.models.member import Member
from app.models.user import User
from app.schemas.member import MemberRegister, MemberRegisterResponse

router = APIRouter(prefix="/member", tags=["Member - Registration"])


@router.post("/reapply", response_model=MemberRegisterResponse)
def reapply_member(
    request: Request,
    member_code: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    branch_id: int = Form(...),
    date_of_birth: date = Form(...),
    gender: str = Form(...),
    country: str = Form(...),
    state: str = Form(...),
    district: str = Form(...),
    city: str = Form(...),
    street: str = Form(...),
    building_no: str = Form(...),
    zip_code: str = Form(...),
    mobile: str = Form(...),
    aadhaar_number: str = Form(...),
    pan_number: str = Form(...),
    bank_holder_name: str = Form(...),
    bank_account_number: str = Form(...),
    ifsc_code: str = Form(...),
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    pan_image: UploadFile = File(...),
    passbook_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. identity: member code + password
    user = db.query(User).filter(
        User.user_code == member_code.strip(),
        User.role == "member",
        User.is_deleted == False,
    ).first()
    verify_login(
        db, user, password, "Incorrect member code or password",
        request=request, expected_role="member", event_context="member_reapply",
    )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is disabled. Contact your branch")

    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Member profile not found")
    if member.status != "rejected":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Re-apply is only for rejected members. Your status is {member.status}")

    # 2. validate text fields (email + password reused from account)
    try:
        data = MemberRegister(
            email=user.email, full_name=full_name, password=password, confirm_password=password,
            branch_id=branch_id, date_of_birth=date_of_birth, gender=gender, country=country,
            state=state, district=district, city=city, street=street, building_no=building_no,
            zip_code=zip_code, mobile=mobile, aadhaar_number=aadhaar_number, pan_number=pan_number,
            bank_holder_name=bank_holder_name, bank_account_number=bank_account_number,
            ifsc_code=ifsc_code,
        )
    except ValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            e.errors(include_url=False, include_context=False, include_input=False),
        )

    # 3. branch check
    branch = db.query(Branch).filter(Branch.id == data.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    if not branch.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This branch is not active. Try another branch.")

    # 4. duplicate checks (ignore own record)
    if db.query(Member).filter(Member.aadhaar_number == data.aadhaar_number, Member.id != member.id).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Aadhaar number already registered")
    if db.query(Member).filter(Member.pan_number == data.pan_number, Member.id != member.id).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "PAN number already registered")

    # 5. images
    images = {
        "aadhaar_front": read_image(aadhaar_front, "Aadhaar front image"),
        "aadhaar_back": read_image(aadhaar_back, "Aadhaar back image"),
        "pan_image": read_image(pan_image, "PAN card image"),
        "passbook_image": read_image(passbook_image, "Bank passbook photo"),
    }

    # 6. replace files + update rows
    try:
        delete_member_files(user.user_code)
        paths = save_member_files(user.user_code, images)

        user.full_name = data.full_name
        user.contact_number = data.mobile
        user.branch_id = data.branch_id

        member.date_of_birth = data.date_of_birth
        member.gender = data.gender
        member.country = data.country
        member.state = data.state
        member.district = data.district
        member.city = data.city
        member.street = data.street
        member.building_no = data.building_no
        member.zip_code = data.zip_code
        member.aadhaar_number = data.aadhaar_number
        member.pan_number = data.pan_number
        member.bank_holder_name = data.bank_holder_name
        member.bank_account_number = data.bank_account_number
        member.ifsc_code = data.ifsc_code
        member.aadhaar_front_path = paths["aadhaar_front"]
        member.aadhaar_back_path = paths["aadhaar_back"]
        member.pan_image_path = paths["pan_image"]
        member.passbook_image_path = paths["passbook_image"]

        member.status = "pending"
        member.rejection_reason = None
        member.reviewed_by = None
        member.reviewed_at = None
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Aadhaar or PAN already registered")
    except Exception:
        db.rollback()
        raise

    return MemberRegisterResponse(
        message="Re-application submitted. Your account is pending approval.",
        member_code=user.user_code,
        status="pending",
    )