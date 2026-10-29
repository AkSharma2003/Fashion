
"""add email to staff users

Revision ID: 6eb4354ed8c9
Revises: e30c3691c0b6
"""
from alembic import op
import sqlalchemy as sa


revision = "6eb4354ed8c9"
down_revision = "e30c3691c0b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_users",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_staff_users_email",
        "staff_users",
        ["email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_staff_users_email", table_name="staff_users")
    op.drop_column("staff_users", "email")
