# FashionOS

One system for the client's fashion business: **shop (billing counter) + website**, one shared stock,
khata (credit) with WhatsApp bills, Tally integration, employees, saree fall-pico and AI helpers.

Requirements: see `docs/README.md` (SRS v1.0 and the Complete Project Documentation).

## Stack (decided)
FastAPI (Python) | React + Vite + TypeScript | PostgreSQL (+ pgvector) | Celery + Redis

## Layout
```
apps/web           React: website, back office, POS (offline), portal pages
apps/api           FastAPI modular monolith (one folder per business module)
apps/ai-service    AI service (separate, with timeouts and fallbacks)
apps/worker        Celery jobs: outbox, reminders, Tally sync, reconciliation
apps/tally-bridge  Windows agent that sits next to Tally (outbound only)
packages/          shared-types, config
database/          seeds and SQL policies (append-only rules)
docs/              SRS, ADRs, runbooks
infrastructure/    docker, caddy, deployment, monitoring
tests/             e2e, contracts, load, offline-sync, tally-sync
scripts/           helpers (new_module.py)
```

## Quick start
```bash
cp .env.example .env
docker compose up -d                      # PostgreSQL (pgvector) + Redis

# API
cd apps/api
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000             # http://localhost:8000/docs

# Web (new terminal, from repo root)
pnpm install
pnpm dev:web                                          # http://localhost:5173
```

## Build order (shop is already trading, so it goes live step by step)
1. Workspace, API and web base (this skeleton)
2. Catalog and stock (`stock_movements` ledger), data import from Tally
3. Tally bridge, tested on a **Tally demo company** first (coexistence mode: counter still bills as today)
4. Khata, WhatsApp bills, Pay Now
5. POS billing and offline mode, then cutover for the counter after a clean parallel run
6. Employees, fall-pico, purchasing
7. Website checkout and orders
8. AI features (Phase 2 and 3)

## Rules that must not be broken
- Money is an integer in **paise**. Never use floats for money.
- Ledgers, stock movements and audit logs are **append-only** (see `database/policies/`). Fix mistakes with a reversing entry.
- Anything that must reach Tally or WhatsApp goes through the **outbox** in the same transaction as the sale.
- Every bill has an **idempotency key**. A retry never makes a second bill.
- Do not create files just to match the tree. Add modules in the build order above (`python scripts/new_module.py <name>`).
