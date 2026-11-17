"""create FD/MIS schemes

Revision ID: 41b7e9c2a6d0
Revises: 98c9d2a4f6b1
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "41b7e9c2a6d0"
down_revision: Union[str, Sequence[str], None] = "98c9d2a4f6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fd_mis_schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_name", sa.String(length=100), nullable=False),
        sa.Column("scheme_code", sa.String(length=20), nullable=False),
        sa.Column("minimum_fd_mis_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("fd_mis_lock_in_period_months", sa.Integer(), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("senior_citizen_addon_interest_rate", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("interest_lock_in_period_months", sa.Integer(), nullable=False),
        sa.Column("tenure_value", sa.Integer(), nullable=False),
        sa.Column("tenure_unit", sa.String(length=10), nullable=False),
        sa.Column("bonus_rate", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("bonus_rate_type", sa.String(length=10), nullable=False),
        sa.Column("cancellation_charges", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cancellation_charges_type", sa.String(length=10), nullable=False),
        sa.Column("penal_charges_percent", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("stationary_charges", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("interest_payout_type", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fd_mis_schemes_id"), "fd_mis_schemes", ["id"], unique=False)
    op.create_index(
        "uq_fd_mis_schemes_code_not_deleted",
        "fd_mis_schemes",
        ["scheme_code"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
        sqlite_where=sa.text("is_deleted = 0"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_fd_mis_schemes_code_not_deleted",
        table_name="fd_mis_schemes",
        postgresql_where=sa.text("is_deleted = false"),
        sqlite_where=sa.text("is_deleted = 0"),
    )
    op.drop_index(op.f("ix_fd_mis_schemes_id"), table_name="fd_mis_schemes")
    op.drop_table("fd_mis_schemes")
