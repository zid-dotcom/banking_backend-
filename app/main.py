from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.branch import Branch 
from app.models.member import Member
from app.routers import (auth, branches, branch_admins, branch_admin_auth,
                         member_register, member_auth, branch_admin_members, member_reapply,
                         superadmin_members, member_nominee, branch_admin_nominees,
                         superadmin_staff_roles, branch_admin_staff, staff_auth,
                         superadmin_loan_schemes,
                         superadmin_staff, branch_admin_loan_schemes,
                         member_loan_schemes, superadmin_savings_schemes,
                         branch_admin_savings_schemes, member_savings_schemes,
                         superadmin_fd_mis_schemes, branch_admin_fd_mis_schemes,
                         member_fd_mis_schemes, branch_admin_staff_roles,
                         member_savings_accounts, branch_admin_savings_accounts,
                         savings_accounts_admin,
                         cash_transactions,
                         cash_reconciliation,
                         superadmin_announcements, branch_admin_announcements,
                         member_announcements, member_service_requests,
                         branch_admin_service_requests, superadmin_service_requests,
                         member_notifications, branch_admin_emergency_cases,
                         superadmin_emergency_cases, member_nominee_change_requests,
                         branch_admin_nominee_change_requests,
                         superadmin_security_events, branch_admin_security_events,
                         member_security_events, staff_security_events)
def seed_superadmin():
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.role == "superadmin").first()
        if not exists:
            db.add(User(
                full_name=settings.SUPERADMIN_NAME,
                email=settings.SUPERADMIN_EMAIL,
                hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
                role="superadmin",
            ))
            db.commit()
            print("Superadmin created")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_superadmin()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(branches.router)
app.include_router(superadmin_members.router)
app.include_router(branch_admins.router)
app.include_router(branch_admin_auth.router)
app.include_router(member_register.router)
app.include_router(member_auth.router)
app.include_router(branch_admin_members.router)
app.include_router(member_reapply.router)
app.include_router(member_nominee.router)
app.include_router(branch_admin_nominees.router)
app.include_router(superadmin_staff_roles.router)
app.include_router(branch_admin_staff.router)
app.include_router(staff_auth.router)
app.include_router(superadmin_staff.router)
app.include_router(superadmin_loan_schemes.router)
app.include_router(branch_admin_loan_schemes.router)
app.include_router(member_loan_schemes.router)
app.include_router(superadmin_savings_schemes.router)
app.include_router(branch_admin_savings_schemes.router)
app.include_router(member_savings_schemes.router)
app.include_router(superadmin_fd_mis_schemes.router)
app.include_router(branch_admin_fd_mis_schemes.router)
app.include_router(member_fd_mis_schemes.router)
app.include_router(member_savings_accounts.router)
app.include_router(branch_admin_savings_accounts.router)
app.include_router(savings_accounts_admin.branch_admin_router)
app.include_router(savings_accounts_admin.superadmin_router)
app.include_router(cash_transactions.staff_router)
app.include_router(cash_transactions.branch_admin_router)
app.include_router(cash_transactions.superadmin_router)
app.include_router(cash_transactions.member_router)
app.include_router(cash_reconciliation.cashier_router)
app.include_router(cash_reconciliation.accountant_router)
app.include_router(cash_reconciliation.branch_admin_router)
app.include_router(branch_admin_staff_roles.router)
app.include_router(superadmin_announcements.router)
app.include_router(branch_admin_announcements.router)
app.include_router(member_announcements.router)
app.include_router(member_service_requests.router)
app.include_router(branch_admin_service_requests.router)
app.include_router(superadmin_service_requests.router)
app.include_router(member_notifications.router)
app.include_router(branch_admin_emergency_cases.router)
app.include_router(superadmin_emergency_cases.router)
app.include_router(member_nominee_change_requests.router)
app.include_router(branch_admin_nominee_change_requests.router)
app.include_router(superadmin_security_events.router)
app.include_router(branch_admin_security_events.router)
app.include_router(member_security_events.router)
app.include_router(staff_security_events.router)


@app.get("/")
def root():
    return {"status": "Banking API running"}