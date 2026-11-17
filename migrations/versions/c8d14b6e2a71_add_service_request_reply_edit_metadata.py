"""add service request reply edit metadata

Revision ID: c8d14b6e2a71
Revises: d7f0a2b91c63
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d14b6e2a71"
down_revision: Union[str, Sequence[str], None] = "d7f0a2b91c63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_request_replies",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "service_request_replies",
        sa.Column("edited_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_service_request_replies_edited_by_id_users",
        "service_request_replies",
        "users",
        ["edited_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_service_request_replies_edited_by_id_users",
        "service_request_replies",
        type_="foreignkey",
    )
    op.drop_column("service_request_replies", "edited_by_id")
    op.drop_column("service_request_replies", "edited_at")
