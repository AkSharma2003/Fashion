
"""add products table

Revision ID: ec2cb1f3dec9
Revises: c6de5b9d75d0
Create Date: 2026-10-11 19:54:27.655952
"""

from alembic import op
import sqlalchemy as sa


revision = "ec2cb1f3dec9"
down_revision = "c6de5b9d75d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("barcode", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("selling_price_paise", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_products_barcode",
        "products",
        ["barcode"],
        unique=True,
    )
    op.create_index(
        "ix_products_category",
        "products",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_products_name",
        "products",
        ["name"],
        unique=False,
    )
    op.create_index(
        "ix_products_sku",
        "products",
        ["sku"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_table("products")
