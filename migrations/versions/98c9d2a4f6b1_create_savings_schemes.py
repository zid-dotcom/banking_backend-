"""create savings schemes

Revision ID: 98c9d2a4f6b1
Revises: 3affd196f0f1
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "98c9d2a4f6b1"
down_revision: Union[str, Sequence[str], None] = "3affd196f0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "savings_schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_name", sa.String(length=100), nullable=False),
        sa.Column("scheme_code", sa.String(length=20), nullable=False),
        sa.Column("min_opening_balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("min_monthly_avg_balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("senior_citizen_addon_interest_rate", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("interest_payout_type", sa.String(length=20), nullable=False),
        sa.Column("lock_in_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("min_monthly_avg_balance_charge", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("service_charge_frequency", sa.String(length=20), nullable=False),
        sa.Column("service_charges", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sms_charge_frequency", sa.String(length=20), nullable=False),
        sa.Column("sms_charges", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_savings_schemes_id"), "savings_schemes", ["id"], unique=False)
    op.create_index(
        "uq_savings_schemes_code_not_deleted",
        "savings_schemes",
        ["scheme_code"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
        sqlite_where=sa.text("is_deleted = 0"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_savings_schemes_code_not_deleted",
        table_name="savings_schemes",
        postgresql_where=sa.text("is_deleted = false"),
        sqlite_where=sa.text("is_deleted = 0"),
    )
    op.drop_index(op.f("ix_savings_schemes_id"), table_name="savings_schemes")
    op.drop_table("savings_schemes")
