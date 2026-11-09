# Local development

## Needs

Python 3.11+, Node.js 20+, pnpm, Docker Desktop, Git. TallyPrime only on the Windows machine that runs the
Tally bridge.

## Repository layout

```
apps/
  api/            FastAPI API (all business rules), Alembic migrations, tests, scripts/seed.py
  web/            React + Vite: website, back office (/backoffice), POS (/pos), Pay Now (/pay/<token>)
  worker/         Celery beat + worker; calls /api/v1/internal/* only
  ai-service/     FastAPI service that calls Claude
  tally-bridge/   Windows agent next to TallyPrime
database/policies SQL kept in sync with the append-only trigger migration
infrastructure/   Caddyfile (production web server)
docs/             This documentation, SRS, project report, ADRs
packages/         Shared front-end packages
```

## First run

```bash
# 1. Databases (PostgreSQL 16 with pgvector, Redis, Mailpit for test e-mail)
cp .env.example apps/api/.env       # set JWT_SECRET, PAYLINK_SECRET, TALLY_AGENT_API_KEY, INTERNAL_API_KEY
docker compose up -d

# 2. API
cd apps/api
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed --phone 9999999999 --password owner123 --pin 1234 --demo
uvicorn app.main:app --reload --port 8000              # http://localhost:8000/docs

# 3. Web (from the repo root)
pnpm install
pnpm dev:web                                           # http://localhost:5173
```

`scripts.seed` creates the roles, the owner login, counter `C1`, and with `--demo` sample products, a customer
with khata and a fall-pico worker. Run it again safely; it skips what exists.

Optional, each in its own terminal:

```bash
pnpm dev:worker      # or: cd apps/worker && celery -A app.celery_app worker -B
pnpm dev:ai          # or: cd apps/ai-service && uvicorn app.main:app --port 8001
```

Without the worker, messages and Tally vouchers wait in the outbox (nothing is lost). Without the AI service,
every AI feature shows its fallback.

## Where to log in

| Screen | URL | Login |
|---|---|---|
| Website | `/` | none; customer login at `/login` → "Customer" |
| Back office | `/backoffice` | `/login` with the owner phone + password from the seed (one login page for staff and customers) |
| POS | `/pos` | staff login once on that device; works offline after |
| Pay Now | `/pay/<token>` | the token in the WhatsApp link (create one in Khata → "Send Pay Now link") |
| Test e-mail | `http://localhost:8025` | Mailpit |

Without Razorpay keys the Pay Now and checkout pages show a "Simulate payment" button (local only).

## Tests

```bash
cd apps/api && pytest                 # ~95 tests on SQLite; 2 in test_auth_repository.py need the Docker PostgreSQL
cd apps/web && npx tsc --noEmit       # type check
pnpm build:web                        # production build
```

See [../testing.md](../testing.md) for what each test covers.

## Adding a module

```bash
python scripts/new_module.py <name>   # creates apps/api/app/modules/<name>/{models,service,repository,router,schemas,events}.py
```

Then add the name to `MODULES` in `apps/api/app/modules/__init__.py`, import its models in
`apps/api/app/models_registry.py`, and make a migration:

```bash
cd apps/api
alembic revision --autogenerate -m "add <name>"
alembic upgrade head && alembic check          # check must say no new operations
python -m scripts.gen_api_docs                 # refresh docs/api/endpoints.md
```

## Code rules

- Business rules go in `service.py`; routers only parse input, check the role and call the service.
- Money is `int` paise. Use `app/core/money.format_inr` to show it.
- Never `UPDATE`/`DELETE` an append-only table; post a reversing entry.
- Side effects (Tally, WhatsApp) go through `app/core/outbox.py`, in the same transaction as the change.
- Raise `BusinessError(code, message, status)` for user-facing errors; the handler builds the envelope.
- Every AI call goes through `assist/gateway.ask` and must have a fallback.
- The web app calls the API only through `apps/web/src/lib/api/client.ts`.

## Common problems

| Problem | Fix |
|---|---|
| `alembic`: "No module named app" | Run it from `apps/api` (`alembic.ini` has `prepend_sys_path = .`) |
| Port 5432 already used | Stop the local PostgreSQL, or change the port in `docker-compose.yml` and `DATABASE_URL` |
| Login works but every call is 401 | Clock or `JWT_SECRET` changed; log in again |
| CORS error in the browser | Add the web origin to `CORS_ORIGINS` |
| `pnpm build:web` changes tracked files in `apps/web/dist` | Do not commit build output; `git checkout apps/web/dist` |
