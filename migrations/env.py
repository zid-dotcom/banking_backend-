from alembic import context
from app.core.database import Base, engine
from app.models.branch import Branch
from app.models.member import Member
from app.models.nominee import Nominee
from app.models.staff_role import StaffRole
from app.models.staff import Staff
from app.models.loan_scheme import LoanScheme
from app.models.savings_scheme import SavingsScheme
from app.models.savings_account import SavingsAccount, SavingsAccountOpeningRequest
from app.models.cash_transaction import CashTransaction
from app.models.cash_reconciliation import CashReconciliation
from app.models.fd_mis_scheme import FdMisScheme
from app.models.announcement import Announcement
from app.models.service_request import ServiceRequest, ServiceRequestReply
from app.models.notification import Notification
from app.models.emergency_case import EmergencyCase, EmergencyCaseMessage
from app.models.nominee_change_request import NomineeChangeRequest
from app.models.security_event import SecurityEvent
from app.models.user import User

config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
