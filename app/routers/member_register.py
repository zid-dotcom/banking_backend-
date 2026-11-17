from datetime import date
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.core.uploads import delete_member_files, read_image, save_member_files
from app.models.branch import Branch
from app.models.member import Member
from app.models.user import User
from app.routers.branch_admins import generate_user_code
from app.schemas.member import BranchPublic, MemberRegister, MemberRegisterResponse

router = APIRouter(prefix="/member", tags=["Member - Registration"])


@router.get("/branches", response_model=List[BranchPublic])
def list_active_branches(db: Session = Depends(get_db)):
    return (
        db.query(Branch)
        .filter(Branch.is_active == True, Branch.is_deleted == False)
        .order_by(Branch.name)
        .all()
    )


@router.post("/register", response_model=MemberRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_member(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
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
    # 1. validate text fields
    try:
        data = MemberRegister(
            email=email, full_name=full_name, password=password, confirm_password=confirm_password,
            branch_id=branch_id, date_of_birth=date_of_birth, gender=gender, country=country,
            state=state, district=district, city=city, street=street, building_no=building_no,
            zip_code=zip_code, mobile=mobile, aadhaar_number=aadhaar_number, pan_number=pan_number,
            bank_holder_name=bank_holder_name, bank_account_number=bank_account_number,
            ifsc_code=ifsc_code,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(include_url=False, include_context=False, include_input=False),
        )

    # 2. branch check
    branch = db.query(Branch).filter(Branch.id == data.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    if not branch.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This branch is not active. Try another branch.")

    # 3. duplicate checks
    email_lower = data.email.lower()
    if db.query(User).filter(User.email == email_lower).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if db.query(Member).filter(Member.aadhaar_number == data.aadhaar_number).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Aadhaar number already registered")
    if db.query(Member).filter(Member.pan_number == data.pan_number).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "PAN number already registered")

    # 4. validate images
    images = {
        "aadhaar_front": read_image(aadhaar_front, "Aadhaar front image"),
        "aadhaar_back": read_image(aadhaar_back, "Aadhaar back image"),
        "pan_image": read_image(pan_image, "PAN card image"),
        "passbook_image": read_image(passbook_image, "Bank passbook photo"),
    }

    # 5. save files + database rows
    member_code = generate_user_code(db)
    try:
        paths = save_member_files(member_code, images)

        user = User(
            user_code=member_code,
            full_name=data.full_name,
            email=email_lower,
            hashed_password=hash_password(data.password),
            contact_number=data.mobile,
            role="member",
            branch_id=data.branch_id,
            is_active=True,
        )
        db.add(user)
        db.flush()  # get user.id

        db.add(Member(
            user_id=user.id,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            country=data.country,
            state=data.state,
            district=data.district,
            city=data.city,
            street=data.street,
            building_no=data.building_no,
            zip_code=data.zip_code,
            aadhaar_number=data.aadhaar_number,
            pan_number=data.pan_number,
            bank_holder_name=data.bank_holder_name,
            bank_account_number=data.bank_account_number,
            ifsc_code=data.ifsc_code,
            aadhaar_front_path=paths["aadhaar_front"],
            aadhaar_back_path=paths["aadhaar_back"],
            pan_image_path=paths["pan_image"],
            passbook_image_path=paths["passbook_image"],
            status="pending",
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        delete_member_files(member_code)
        raise HTTPException(status.HTTP_409_CONFLICT, "Email, Aadhaar or PAN already registered")
    except Exception:
        db.rollback()
        delete_member_files(member_code)
        raise

    return MemberRegisterResponse(
        message="Registration successful. Your account is pending approval.",
        member_code=member_code,
        status="pending",
    )