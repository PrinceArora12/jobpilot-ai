"""rapid apply: queue table + job/application/profile latency & opt-in columns

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("detected_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("normalized_at", sa.DateTime(timezone=True)))

    op.add_column("applications", sa.Column("application_started_at", sa.DateTime(timezone=True)))
    op.add_column("applications", sa.Column("application_completed_at", sa.DateTime(timezone=True)))

    op.add_column(
        "profiles",
        sa.Column("rapid_apply_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "profiles",
        sa.Column("min_match_score_to_apply", sa.Integer(), nullable=False, server_default="60"),
    )

    op.create_table(
        "rapid_apply_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("source_posted_at", sa.DateTime(timezone=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("detected_at", sa.DateTime(timezone=True)),
        sa.Column("normalized_at", sa.DateTime(timezone=True)),
        sa.Column("matched_at", sa.DateTime(timezone=True)),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("application_started_at", sa.DateTime(timezone=True)),
        sa.Column("application_completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", name="uq_rapid_apply_queue_user_job"),
    )
    op.create_index("ix_rapid_apply_queue_user_id", "rapid_apply_queue", ["user_id"])
    op.create_index("ix_rapid_apply_queue_job_id", "rapid_apply_queue", ["job_id"])
    op.create_index("ix_rapid_apply_queue_priority", "rapid_apply_queue", ["priority"])
    op.create_index("ix_rapid_apply_queue_status", "rapid_apply_queue", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rapid_apply_queue_status", table_name="rapid_apply_queue")
    op.drop_index("ix_rapid_apply_queue_priority", table_name="rapid_apply_queue")
    op.drop_index("ix_rapid_apply_queue_job_id", table_name="rapid_apply_queue")
    op.drop_index("ix_rapid_apply_queue_user_id", table_name="rapid_apply_queue")
    op.drop_table("rapid_apply_queue")

    op.drop_column("profiles", "min_match_score_to_apply")
    op.drop_column("profiles", "rapid_apply_enabled")

    op.drop_column("applications", "application_completed_at")
    op.drop_column("applications", "application_started_at")

    op.drop_column("jobs", "normalized_at")
    op.drop_column("jobs", "detected_at")
