
"""add inventory variant stock tables

Revision ID: f63f2a1a9195
Revises: ec2cb1f3dec9
"""

from alembic import op
import sqlalchemy as sa


revision = "f63f2a1a9195"
down_revision = "ec2cb1f3dec9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(
        op.f("ix_variants_product_id"),
        "variants",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "barcodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        op.f("ix_barcodes_variant_id"),
        "barcodes",
        ["variant_id"],
        unique=False,
    )

    op.create_table(
        "stock_levels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("on_hand", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "on_hand >= 0",
            name="ck_stock_levels_on_hand_nonnegative",
        ),
        sa.CheckConstraint(
            "reserved >= 0",
            name="ck_stock_levels_reserved_nonnegative",
        ),
        sa.CheckConstraint(
            "reserved <= on_hand",
            name="ck_stock_levels_reserved_lte_on_hand",
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id", name="uq_stock_levels_variant"),
    )
    op.create_index(
        op.f("ix_stock_levels_variant_id"),
        "stock_levels",
        ["variant_id"],
        unique=False,
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("reference_type", sa.String(length=40), nullable=True),
        sa.Column("reference_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity_delta != 0",
            name="ck_stock_movement_nonzero",
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_movements_variant_id"),
        "stock_movements",
        ["variant_id"],
        unique=False,
    )

    op.create_table(
        "stock_counts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        sa.Column("counted_quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "counted_quantity >= 0",
            name="ck_stock_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_counts_variant_id"),
        "stock_counts",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_stock_counts_variant_id"),
        table_name="stock_counts",
    )
    op.drop_table("stock_counts")

    op.drop_index(
        op.f("ix_stock_movements_variant_id"),
        table_name="stock_movements",
    )
    op.drop_table("stock_movements")

    op.drop_index(
        op.f("ix_stock_levels_variant_id"),
        table_name="stock_levels",
    )
    op.drop_table("stock_levels")

    op.drop_index(
        op.f("ix_barcodes_variant_id"),
        table_name="barcodes",
    )
    op.drop_table("barcodes")

    op.drop_index(
        op.f("ix_variants_product_id"),
        table_name="variants",
    )
    op.drop_table("variants")
