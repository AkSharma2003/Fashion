"""shops: three shops (Sethi Saree Sansar, Sethi Suit, Sethi Kids); stock, counters, bills, staff per shop

All existing data belongs to the main shop (Sethi Saree Sansar).

Revision ID: 743496565ef6
Revises: 551c9a825339
Create Date: 2026-11-10 13:32:15.277720
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = '743496565ef6'
down_revision = '551c9a825339'
branch_labels = None
depends_on = None

MAIN = str(uuid.uuid5(uuid.NAMESPACE_URL, "wearverse/shop/SSS"))
SHOPS = [(MAIN, "SSS", "Sethi Saree Sansar", True),
         (str(uuid.uuid5(uuid.NAMESPACE_URL, "wearverse/shop/SS")), "SS", "Sethi Suit", False),
         (str(uuid.uuid5(uuid.NAMESPACE_URL, "wearverse/shop/SK")), "SK", "Sethi Kids", False)]
NULLABLE = ["bills", "counters", "order_items", "staff_users", "stock_counts", "purchases", "purchase_orders"]


def upgrade() -> None:
    op.create_table(
        'shops',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=8), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('gstin', sa.String(length=15), nullable=True),
        sa.Column('state_code', sa.String(length=2), nullable=True),
        sa.Column('address', sa.String(length=300), nullable=True),
        sa.Column('phone', sa.String(length=15), nullable=True),
        sa.Column('tally_company', sa.String(length=100), nullable=True),
        sa.Column('is_main', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    shops = sa.table('shops', sa.column('id', sa.Uuid), sa.column('code', sa.String), sa.column('name', sa.String),
                     sa.column('is_main', sa.Boolean), sa.column('is_active', sa.Boolean))
    op.bulk_insert(shops, [{"id": uuid.UUID(i), "code": c, "name": n, "is_main": m, "is_active": True}
                           for i, c, n, m in SHOPS])
    # The old single-shop GSTIN / state from Settings belong to the main shop.
    op.execute(f"""UPDATE shops SET gstin = NULLIF(TRIM(BOTH '"' FROM (SELECT value::text FROM settings WHERE key = 'shop_gstin')), ''),
                   state_code = NULLIF(TRIM(BOTH '"' FROM (SELECT value::text FROM settings WHERE key = 'shop_state_code')), '')
                   WHERE id = '{MAIN}'""")

    for table in NULLABLE:
        op.add_column(table, sa.Column('shop_id', sa.Uuid(), nullable=True))
        op.create_index(f'ix_{table}_shop_id', table, ['shop_id'], unique=False)
        op.create_foreign_key(f'fk_{table}_shop', table, 'shops', ['shop_id'], ['id'])
    for table in ("bills", "counters", "order_items", "stock_counts", "purchases", "purchase_orders"):
        op.execute(f"UPDATE {table} SET shop_id = '{MAIN}'")
    # staff_users stay NULL = all shops (an owner/manager can then be tied to one shop in Settings).

    op.add_column('stock_levels', sa.Column('shop_id', sa.Uuid(), nullable=True))
    op.execute(f"UPDATE stock_levels SET shop_id = '{MAIN}'")
    op.alter_column('stock_levels', 'shop_id', nullable=False)
    op.drop_constraint('uq_stock_levels_variant', 'stock_levels', type_='unique')
    op.create_index('ix_stock_levels_shop_id', 'stock_levels', ['shop_id'], unique=False)
    op.create_unique_constraint('uq_stock_levels_variant_shop', 'stock_levels', ['variant_id', 'shop_id'])
    op.create_foreign_key('fk_stock_levels_shop', 'stock_levels', 'shops', ['shop_id'], ['id'])

    # stock_movements is append-only (trigger); this one-time backfill is the only allowed change.
    op.add_column('stock_movements', sa.Column('shop_id', sa.Uuid(), nullable=True))
    op.execute('ALTER TABLE stock_movements DISABLE TRIGGER "stock_movements_append_only"')
    op.execute(f"UPDATE stock_movements SET shop_id = '{MAIN}'")
    op.execute('ALTER TABLE stock_movements ENABLE TRIGGER "stock_movements_append_only"')
    op.alter_column('stock_movements', 'shop_id', nullable=False)
    op.create_index('ix_stock_movements_shop_id', 'stock_movements', ['shop_id'], unique=False)
    op.create_foreign_key('fk_stock_movements_shop', 'stock_movements', 'shops', ['shop_id'], ['id'])

    # The existing counter C1 belongs to the main shop; new counters get shop codes (SS-C1, SK-C1).
    op.execute(f"UPDATE counters SET shop_id = '{MAIN}' WHERE shop_id IS NULL")
    op.execute(f"""INSERT INTO counters (id, code, name, is_active, shop_id, created_at)
                   SELECT '{uuid.uuid5(uuid.NAMESPACE_URL, "wearverse/counter/SS-C1")}', 'SS-C1', 'Sethi Suit counter 1', true, '{SHOPS[1][0]}', now()
                   WHERE NOT EXISTS (SELECT 1 FROM counters WHERE code = 'SS-C1')""")
    op.execute(f"""INSERT INTO counters (id, code, name, is_active, shop_id, created_at)
                   SELECT '{uuid.uuid5(uuid.NAMESPACE_URL, "wearverse/counter/SK-C1")}', 'SK-C1', 'Sethi Kids counter 1', true, '{SHOPS[2][0]}', now()
                   WHERE NOT EXISTS (SELECT 1 FROM counters WHERE code = 'SK-C1')""")


def downgrade() -> None:
    # Going back to one shop keeps only the main shop's stock rows (others cannot fit the old one-row-per-variant shape).
    op.execute("DELETE FROM counters WHERE code IN ('SS-C1', 'SK-C1') AND NOT EXISTS (SELECT 1 FROM bills b WHERE b.counter_code = counters.code)")
    op.drop_constraint('fk_stock_movements_shop', 'stock_movements', type_='foreignkey')
    op.drop_index('ix_stock_movements_shop_id', table_name='stock_movements')
    op.drop_column('stock_movements', 'shop_id')
    op.drop_constraint('fk_stock_levels_shop', 'stock_levels', type_='foreignkey')
    op.drop_constraint('uq_stock_levels_variant_shop', 'stock_levels', type_='unique')
    op.drop_index('ix_stock_levels_shop_id', table_name='stock_levels')
    op.execute(f"DELETE FROM stock_levels WHERE shop_id <> '{MAIN}'")
    op.create_unique_constraint('uq_stock_levels_variant', 'stock_levels', ['variant_id'])
    op.drop_column('stock_levels', 'shop_id')
    for table in reversed(NULLABLE):
        op.drop_constraint(f'fk_{table}_shop', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_shop_id', table_name=table)
        op.drop_column(table, 'shop_id')
    op.drop_table('shops')
