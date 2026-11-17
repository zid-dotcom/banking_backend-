"""add branch IFSC code

Revision ID: 4c6a9f12d8b3
Revises: 7b3e1a9c5d42
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c6a9f12d8b3"
down_revision: Union[str, Sequence[str], None] = "7b3e1a9c5d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("ifsc_code", sa.String(length=11), nullable=True))
    op.create_index("uq_branches_ifsc_code", "branches", ["ifsc_code"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_branches_ifsc_code", table_name="branches")
    op.drop_column("branches", "ifsc_code")
