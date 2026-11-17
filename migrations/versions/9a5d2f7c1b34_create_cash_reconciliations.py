"""create cashier cash reconciliations

Revision ID: 9a5d2f7c1b34
Revises: c8254e71a9d2
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a5d2f7c1b34"
down_revision: Union[str, Sequence[str], None] = "c8254e71a9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cash_reconciliations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("cashier_user_id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("opening_cash", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("closing_cash", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column(
            "deposit_total",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "withdrawal_total",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("expected_closing_cash", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("difference", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("accountant_user_id", sa.Integer(), nullable=True),
        sa.Column("accountant_explanation", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["cashier_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accountant_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cashier_user_id",
            "business_date",
            name="uq_cash_reconciliations_cashier_date",
        ),
    )
    op.create_index(
        op.f("ix_cash_reconciliations_id"),
        "cash_reconciliations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cash_reconciliations_branch_id"),
        "cash_reconciliations",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cash_reconciliations_cashier_user_id"),
        "cash_reconciliations",
        ["cashier_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_cash_reconciliations_branch_date",
        "cash_reconciliations",
        ["branch_id", "business_date"],
        unique=False,
    )
    op.create_index(
        "ix_cash_reconciliations_cashier_date",
        "cash_reconciliations",
        ["cashier_user_id", "business_date"],
        unique=False,
    )
    op.create_index(
        "uq_cash_reconciliations_one_open_per_cashier",
        "cash_reconciliations",
        ["cashier_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cash_reconciliations_one_open_per_cashier",
        table_name="cash_reconciliations",
        postgresql_where=sa.text("status = 'open'"),
        sqlite_where=sa.text("status = 'open'"),
    )
    op.drop_index("ix_cash_reconciliations_cashier_date", table_name="cash_reconciliations")
    op.drop_index("ix_cash_reconciliations_branch_date", table_name="cash_reconciliations")
    op.drop_index(op.f("ix_cash_reconciliations_cashier_user_id"), table_name="cash_reconciliations")
    op.drop_index(op.f("ix_cash_reconciliations_branch_id"), table_name="cash_reconciliations")
    op.drop_index(op.f("ix_cash_reconciliations_id"), table_name="cash_reconciliations")
    op.drop_table("cash_reconciliations")
