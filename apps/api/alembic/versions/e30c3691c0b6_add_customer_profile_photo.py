
"""add customer profile photo

Revision ID: e30c3691c0b6
Revises: d6b52b0b7a3f
"""

from alembic import op
import sqlalchemy as sa

revision = "e30c3691c0b6"
down_revision = "d6b52b0b7a3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("profile_photo_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customers", "profile_photo_url")
