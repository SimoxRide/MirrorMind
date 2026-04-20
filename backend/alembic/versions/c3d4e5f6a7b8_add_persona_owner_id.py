"""add_persona_owner_id

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persona_cores",
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_persona_cores_owner_id", "persona_cores", ["owner_id"], unique=False
    )
    op.create_foreign_key(
        "fk_persona_cores_owner_id_users",
        "persona_cores",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill: assign existing personas to the first admin (if any).
    # Non-destructive — leaves ownerless personas untouched if no admin exists.
    op.execute(
        """
        UPDATE persona_cores
        SET owner_id = (
            SELECT id FROM users WHERE is_admin = TRUE ORDER BY created_at ASC LIMIT 1
        )
        WHERE owner_id IS NULL
          AND EXISTS (SELECT 1 FROM users WHERE is_admin = TRUE)
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_persona_cores_owner_id_users", "persona_cores", type_="foreignkey"
    )
    op.drop_index("ix_persona_cores_owner_id", table_name="persona_cores")
    op.drop_column("persona_cores", "owner_id")
