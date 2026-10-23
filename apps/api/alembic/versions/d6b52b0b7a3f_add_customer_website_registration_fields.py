
"""add customer website registration fields

Revision ID: d6b52b0b7a3f
Revises: 5775df26eb00
"""

from alembic import op
import sqlalchemy as sa

revision = "d6b52b0b7a3f"
down_revision = "5775df26eb00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.create_unique_constraint(
        "uq_customers_email",
        "customers",
        ["email"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_customers_email",
        "customers",
        type_="unique",
    )
    op.drop_column("customers", "is_verified")
    op.drop_column("customers", "password_hash")
    op.drop_column("customers", "email")
