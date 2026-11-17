"""create nominee change requests

Revision ID: 4f9b2c1d7a63
Revises: 32f8a6c1d9e4
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f9b2c1d7a63"
down_revision: Union[str, Sequence[str], None] = "32f8a6c1d9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nominee_change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nominee_change_requests_id"),
        "nominee_change_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_nominee_change_requests_member_id"),
        "nominee_change_requests",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        "ix_nominee_change_requests_member_status",
        "nominee_change_requests",
        ["member_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_nominee_change_requests_member_status", table_name="nominee_change_requests")
    op.drop_index(op.f("ix_nominee_change_requests_member_id"), table_name="nominee_change_requests")
    op.drop_index(op.f("ix_nominee_change_requests_id"), table_name="nominee_change_requests")
    op.drop_table("nominee_change_requests")
