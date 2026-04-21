"""add_memory_images_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-21 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_images",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "persona_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("persona_cores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "memory_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("memories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "kind", sa.String(length=20), nullable=False, server_default="memory"
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column(
            "content_type",
            sa.String(length=64),
            nullable=False,
            server_default="image/jpeg",
        ),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "analysis_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "metadata_extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_memory_images_persona_id", "memory_images", ["persona_id"])
    op.create_index("ix_memory_images_memory_id", "memory_images", ["memory_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_images_memory_id", table_name="memory_images")
    op.drop_index("ix_memory_images_persona_id", table_name="memory_images")
    op.drop_table("memory_images")
