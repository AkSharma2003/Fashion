"""fix khata accounts table name

Revision ID: 152997f0bf5e
Revises: 3556b0aa0ec8
Create Date: 2026-10-09 09:30:58.898242
"""
from alembic import op
import sqlalchemy as sa


revision = '152997f0bf5e'
down_revision = '3556b0aa0ec8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("khata_account", "khata_accounts")


def downgrade() -> None:
    op.rename_table("khata_accounts", "khata_account")


