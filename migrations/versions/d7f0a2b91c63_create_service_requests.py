"""create service requests and replies

Revision ID: d7f0a2b91c63
Revises: 65d18a3c4f92
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7f0a2b91c63"
down_revision: Union[str, Sequence[str], None] = "65d18a3c4f92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_requests_id"), "service_requests", ["id"], unique=False)
    op.create_index(op.f("ix_service_requests_member_id"), "service_requests", ["member_id"], unique=False)
    op.create_index(op.f("ix_service_requests_branch_id"), "service_requests", ["branch_id"], unique=False)
    op.create_index("ix_service_requests_branch_status", "service_requests", ["branch_id", "status"], unique=False)
    op.create_index("ix_service_requests_member_created", "service_requests", ["member_id", "created_at"], unique=False)

    op.create_table(
        "service_request_replies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_request_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_request_replies_id"), "service_request_replies", ["id"], unique=False)
    op.create_index(op.f("ix_service_request_replies_service_request_id"), "service_request_replies", ["service_request_id"], unique=False)
    op.create_index(op.f("ix_service_request_replies_sender_id"), "service_request_replies", ["sender_id"], unique=False)
    op.create_index(
        "ix_service_request_replies_request_created",
        "service_request_replies",
        ["service_request_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_service_request_replies_request_created", table_name="service_request_replies")
    op.drop_index(op.f("ix_service_request_replies_sender_id"), table_name="service_request_replies")
    op.drop_index(op.f("ix_service_request_replies_service_request_id"), table_name="service_request_replies")
    op.drop_index(op.f("ix_service_request_replies_id"), table_name="service_request_replies")
    op.drop_table("service_request_replies")
    op.drop_index("ix_service_requests_member_created", table_name="service_requests")
    op.drop_index("ix_service_requests_branch_status", table_name="service_requests")
    op.drop_index(op.f("ix_service_requests_branch_id"), table_name="service_requests")
    op.drop_index(op.f("ix_service_requests_member_id"), table_name="service_requests")
    op.drop_index(op.f("ix_service_requests_id"), table_name="service_requests")
    op.drop_table("service_requests")
