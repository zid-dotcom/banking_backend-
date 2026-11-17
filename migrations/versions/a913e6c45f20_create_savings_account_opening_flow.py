"""create savings account opening flow

Revision ID: a913e6c45f20
Revises: 4c6a9f12d8b3
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a913e6c45f20"
down_revision: Union[str, Sequence[str], None] = "4c6a9f12d8b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "savings_account_opening_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("savings_scheme_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["savings_scheme_id"], ["savings_schemes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_savings_account_opening_requests_id"),
        "savings_account_opening_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_savings_account_opening_requests_member_id"),
        "savings_account_opening_requests",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_savings_account_opening_requests_branch_id"),
        "savings_account_opening_requests",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_savings_account_opening_requests_savings_scheme_id"),
        "savings_account_opening_requests",
        ["savings_scheme_id"],
        unique=False,
    )
    op.create_index(
        "ix_savings_account_opening_requests_branch_status",
        "savings_account_opening_requests",
        ["branch_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_savings_account_opening_requests_member_created",
        "savings_account_opening_requests",
        ["member_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_savings_account_opening_pending_member_scheme",
        "savings_account_opening_requests",
        ["member_id", "savings_scheme_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "savings_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(length=16), nullable=False),
        sa.Column("opening_request_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("savings_scheme_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["opening_request_id"], ["savings_account_opening_requests.id"]),
        sa.ForeignKeyConstraint(["savings_scheme_id"], ["savings_schemes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number"),
        sa.UniqueConstraint("opening_request_id"),
    )
    op.create_index(op.f("ix_savings_accounts_id"), "savings_accounts", ["id"], unique=False)
    op.create_index(
        op.f("ix_savings_accounts_member_id"),
        "savings_accounts",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_savings_accounts_branch_id"),
        "savings_accounts",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_savings_accounts_savings_scheme_id"),
        "savings_accounts",
        ["savings_scheme_id"],
        unique=False,
    )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.alter_column(
            "service_request_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_savings_accounts_savings_scheme_id"), table_name="savings_accounts")
    op.drop_index(op.f("ix_savings_accounts_branch_id"), table_name="savings_accounts")
    op.drop_index(op.f("ix_savings_accounts_member_id"), table_name="savings_accounts")
    op.drop_index(op.f("ix_savings_accounts_id"), table_name="savings_accounts")
    op.drop_table("savings_accounts")

    op.drop_index(
        "uq_savings_account_opening_pending_member_scheme",
        table_name="savings_account_opening_requests",
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )
    op.drop_index(
        "ix_savings_account_opening_requests_member_created",
        table_name="savings_account_opening_requests",
    )
    op.drop_index(
        "ix_savings_account_opening_requests_branch_status",
        table_name="savings_account_opening_requests",
    )
    op.drop_index(
        op.f("ix_savings_account_opening_requests_savings_scheme_id"),
        table_name="savings_account_opening_requests",
    )
    op.drop_index(
        op.f("ix_savings_account_opening_requests_branch_id"),
        table_name="savings_account_opening_requests",
    )
    op.drop_index(
        op.f("ix_savings_account_opening_requests_member_id"),
        table_name="savings_account_opening_requests",
    )
    op.drop_index(
        op.f("ix_savings_account_opening_requests_id"),
        table_name="savings_account_opening_requests",
    )
    op.drop_table("savings_account_opening_requests")

    op.execute(
        "DELETE FROM notifications "
        "WHERE service_request_id IS NULL "
        "AND notification_type LIKE 'savings_account_opening_%'"
    )
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.alter_column(
            "service_request_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
