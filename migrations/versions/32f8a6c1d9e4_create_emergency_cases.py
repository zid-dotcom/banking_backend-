"""create emergency cases and messages

Revision ID: 32f8a6c1d9e4
Revises: e3a91f7c2d54
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "32f8a6c1d9e4"
down_revision: Union[str, Sequence[str], None] = "e3a91f7c2d54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emergency_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_cases_id"), "emergency_cases", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_cases_branch_id"), "emergency_cases", ["branch_id"], unique=False)
    op.create_index(op.f("ix_emergency_cases_created_by_id"), "emergency_cases", ["created_by_id"], unique=False)
    op.create_index("ix_emergency_cases_branch_updated", "emergency_cases", ["branch_id", "updated_at"], unique=False)
    op.create_index("ix_emergency_cases_creator_updated", "emergency_cases", ["created_by_id", "updated_at"], unique=False)

    op.create_table(
        "emergency_case_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["emergency_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_case_messages_id"), "emergency_case_messages", ["id"], unique=False)
    op.create_index(op.f("ix_emergency_case_messages_case_id"), "emergency_case_messages", ["case_id"], unique=False)
    op.create_index(op.f("ix_emergency_case_messages_sender_id"), "emergency_case_messages", ["sender_id"], unique=False)
    op.create_index(
        "ix_emergency_case_messages_case_created",
        "emergency_case_messages",
        ["case_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_emergency_case_messages_read_created",
        "emergency_case_messages",
        ["read_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_emergency_case_messages_read_created", table_name="emergency_case_messages")
    op.drop_index("ix_emergency_case_messages_case_created", table_name="emergency_case_messages")
    op.drop_index(op.f("ix_emergency_case_messages_sender_id"), table_name="emergency_case_messages")
    op.drop_index(op.f("ix_emergency_case_messages_case_id"), table_name="emergency_case_messages")
    op.drop_index(op.f("ix_emergency_case_messages_id"), table_name="emergency_case_messages")
    op.drop_table("emergency_case_messages")
    op.drop_index("ix_emergency_cases_creator_updated", table_name="emergency_cases")
    op.drop_index("ix_emergency_cases_branch_updated", table_name="emergency_cases")
    op.drop_index(op.f("ix_emergency_cases_created_by_id"), table_name="emergency_cases")
    op.drop_index(op.f("ix_emergency_cases_branch_id"), table_name="emergency_cases")
    op.drop_index(op.f("ix_emergency_cases_id"), table_name="emergency_cases")
    op.drop_table("emergency_cases")
