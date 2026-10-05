-- Append-only protection: these tables can be inserted into but never updated or deleted.
-- Run after the migration that creates each table (safe to run again).

CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % is append-only: % is not allowed. Add a reversing entry instead.',
    TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'ledger_entries', 'stock_movements', 'audit_logs',
    'fp_job_events', 'salary_payments', 'advance_recoveries', 'fp_worker_ledger'
  ] LOOP
    IF to_regclass(t) IS NOT NULL THEN
      EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', t || '_append_only', t);
      EXECUTE format(
        'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION forbid_update_delete()',
        t || '_append_only', t);
    END IF;
  END LOOP;
END $$;
