"""add email verification token to users

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verification_token", sa.String(length=255), nullable=True))
    op.add_column(
        "users", sa.Column("verification_token_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_users_verification_token", "users", ["verification_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_verification_token", table_name="users")
    op.drop_column("users", "verification_token_expires_at")
    op.drop_column("users", "verification_token")
