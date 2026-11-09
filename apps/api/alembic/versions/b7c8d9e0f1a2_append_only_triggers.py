"""Append-only triggers on money, stock and audit tables (security checklist #5)

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
"""
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

TABLES = [
    "ledger_entries", "ledger_allocations", "stock_movements", "audit_logs", "fp_job_events",
    "salary_payments", "advance_recoveries", "fp_worker_ledger", "message_events",
    "order_status_logs", "webhook_events",
]

# Same SQL as database/policies/001_append_only.sql (kept inline so the API image needs no extra files).
FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % is append-only: % is not allowed. Add a reversing entry instead.',
    TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(FUNCTION_SQL)
    for table in TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS "{table}_append_only" ON "{table}"')
        op.execute(f'CREATE TRIGGER "{table}_append_only" BEFORE UPDATE OR DELETE ON "{table}" '
                   f'FOR EACH ROW EXECUTE FUNCTION forbid_update_delete()')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS "{table}_append_only" ON "{table}"')
