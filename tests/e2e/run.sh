#!/bin/sh
# One full shop day end to end (staff, POS, khata, Pay Now, website, shipping, fall-pico, buying, salary,
# Tally, AI, reports) on a FRESH throwaway database `wearverse_e2e`. Never touches the real database.
# Needs: docker compose up -d (PostgreSQL, Redis, Mailpit) and apps/api/.venv.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
docker compose exec -T db psql -U fashionos -d postgres -qc "DROP DATABASE IF EXISTS wearverse_e2e;" -qc "CREATE DATABASE wearverse_e2e OWNER fashionos;"
docker compose exec -T redis sh -c "redis-cli --scan --pattern 'wearverse:rl:*' | xargs -r redis-cli del" >/dev/null
cd apps/api
export DATABASE_URL=postgresql+psycopg://fashionos:fashionos@localhost:5432/wearverse_e2e
.venv/bin/alembic upgrade head >/dev/null
.venv/bin/python -m scripts.seed --phone 9999999999 --password owner123 --pin 1234 --demo >/dev/null
rm -f "$ROOT/tests/e2e/failures.log"
PYTHONPATH=. .venv/bin/python "$ROOT/tests/e2e/shop_day.py"
status=$?
cd "$ROOT" && docker compose exec -T db psql -U fashionos -d postgres -qc "DROP DATABASE IF EXISTS wearverse_e2e;"
exit $status
