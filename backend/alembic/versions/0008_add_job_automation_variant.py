"""add jobs.automation_variant (Phase 8 mock form routing)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("automation_variant", sa.String(30), nullable=False, server_default="standard"),
    )


def downgrade() -> None:
    op.drop_column("jobs", "automation_variant")
