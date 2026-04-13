"""add_user_provider_settings

Revision ID: 0d5b0c93c6d1
Revises: 9920f7d4dbbf
Create Date: 2026-04-13 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0d5b0c93c6d1"
down_revision: Union[str, None] = "9920f7d4dbbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("provider_api_key", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("provider_api_base", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("provider_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "provider_model")
    op.drop_column("users", "provider_api_base")
    op.drop_column("users", "provider_api_key")
