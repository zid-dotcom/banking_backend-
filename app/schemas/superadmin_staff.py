from datetime import datetime

from pydantic import BaseModel, EmailStr


class SuperadminStaffOut(BaseModel):
    id: int
    staff_code: str
    full_name: str
    email: EmailStr
    contact_number: str
    address: str
    staff_role_id: int
    staff_role_name: str
    branch_id: int
    branch_code: str
    branch_name: str
    is_active: bool
    branch_is_active: bool
    created_at: datetime
