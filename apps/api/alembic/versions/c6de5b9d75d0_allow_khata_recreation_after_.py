"""allow khata recreation after deactivation

Revision ID: c6de5b9d75d0
Revises: 152997f0bf5e
Create Date: 2026-10-09 09:59:44.370462
"""
from alembic import op
import sqlalchemy as sa


revision = 'c6de5b9d75d0'
down_revision = '152997f0bf5e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the unique constraint on customer_id
    op.drop_constraint(
        "khata_account_customer_id_key",
        "khata_accounts",
        type_="unique",
    )

    # Only one active Khata per customer
    op.create_index(
        "uq_khata_accounts_active_customer",
        "khata_accounts",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_khata_accounts_active_customer",
        table_name="khata_accounts",
    )

    op.create_unique_constraint(
        "khata_account_customer_id_key",
        "khata_accounts",
        ["customer_id"],
    )