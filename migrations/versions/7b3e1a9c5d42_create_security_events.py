"""create security events

Revision ID: 7b3e1a9c5d42
Revises: 4f9b2c1d7a63
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b3e1a9c5d42"
down_revision: Union[str, Sequence[str], None] = "4f9b2c1d7a63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("account_role", sa.String(length=30), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("is_suspicious", sa.Boolean(), nullable=False),
        sa.Column("details", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_security_events_id"), "security_events", ["id"], unique=False)
    op.create_index(op.f("ix_security_events_user_id"), "security_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_security_events_actor_user_id"), "security_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_security_events_branch_id"), "security_events", ["branch_id"], unique=False)
    op.create_index(op.f("ix_security_events_account_role"), "security_events", ["account_role"], unique=False)
    op.create_index(op.f("ix_security_events_event_type"), "security_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_security_events_is_suspicious"), "security_events", ["is_suspicious"], unique=False)
    op.create_index(op.f("ix_security_events_created_at"), "security_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_security_events_created_at"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_is_suspicious"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_event_type"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_account_role"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_branch_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_user_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_user_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_id"), table_name="security_events")
    op.drop_table("security_events")
