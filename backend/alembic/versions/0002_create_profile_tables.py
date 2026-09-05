"""create profile tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("phone", sa.String(30)),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100)),
        sa.Column("linkedin_url", sa.String(255)),
        sa.Column("github_url", sa.String(255)),
        sa.Column("portfolio_url", sa.String(255)),
        sa.Column("job_types", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("work_modes", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("preferred_locations", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("min_salary", sa.Float()),
        sa.Column("experience_level", sa.String(50)),
        sa.Column("preferred_roles", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("preferred_skills", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "education",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("degree", sa.String(150)),
        sa.Column("university", sa.String(200)),
        sa.Column("major", sa.String(150)),
        sa.Column("minor", sa.String(150)),
        sa.Column("graduation_year", sa.Integer()),
        sa.Column("cgpa", sa.Float()),
        sa.Column("relevant_coursework", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "experience",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("company", sa.String(200)),
        sa.Column("position", sa.String(200)),
        sa.Column("start_date", sa.String(20)),
        sa.Column("end_date", sa.String(20)),
        sa.Column("responsibilities", sa.Text()),
        sa.Column("achievements", sa.Text()),
        sa.Column("technologies", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("name", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("technologies", postgresql.ARRAY(sa.String(255)), server_default="{}"),
        sa.Column("github_url", sa.String(255)),
        sa.Column("demo_url", sa.String(255)),
        sa.Column("achievements", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("name", sa.String(200)),
        sa.Column("issuer", sa.String(200)),
        sa.Column("issued_date", sa.String(20)),
        sa.Column("credential_url", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="other"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skills_profile_id", "skills", ["profile_id"])


def downgrade() -> None:
    op.drop_table("skills")
    op.drop_table("certifications")
    op.drop_table("projects")
    op.drop_table("experience")
    op.drop_table("education")
    op.drop_table("profiles")
