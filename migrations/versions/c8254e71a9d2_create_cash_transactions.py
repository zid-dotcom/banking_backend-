"""create cash transactions

Revision ID: c8254e71a9d2
Revises: a913e6c45f20
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8254e71a9d2"
down_revision: Union[str, Sequence[str], None] = "a913e6c45f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cash_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_number", sa.String(length=12), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("balance_before", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["savings_accounts.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_number"),
    )
    op.create_index(op.f("ix_cash_transactions_id"), "cash_transactions", ["id"], unique=False)
    op.create_index(
        op.f("ix_cash_transactions_account_id"),
        "cash_transactions",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cash_transactions_branch_id"),
        "cash_transactions",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cash_transactions_staff_user_id"),
        "cash_transactions",
        ["staff_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_cash_transactions_branch_created",
        "cash_transactions",
        ["branch_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cash_transactions_staff_created",
        "cash_transactions",
        ["staff_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cash_transactions_account_created",
        "cash_transactions",
        ["account_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cash_transactions_account_created", table_name="cash_transactions")
    op.drop_index("ix_cash_transactions_staff_created", table_name="cash_transactions")
    op.drop_index("ix_cash_transactions_branch_created", table_name="cash_transactions")
    op.drop_index(op.f("ix_cash_transactions_staff_user_id"), table_name="cash_transactions")
    op.drop_index(op.f("ix_cash_transactions_branch_id"), table_name="cash_transactions")
    op.drop_index(op.f("ix_cash_transactions_account_id"), table_name="cash_transactions")
    op.drop_index(op.f("ix_cash_transactions_id"), table_name="cash_transactions")
    op.drop_table("cash_transactions")
