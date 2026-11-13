# Architecture overview

WearVerse is a **modular monolith**: one FastAPI API owns every business rule and the one PostgreSQL
database. Everything else (website, POS, worker, AI service, Tally bridge) talks to that API over HTTP.
Requirement IDs (`FR-KHT-02`, `T06`) refer to the SRS in [../srs/srs.pdf](../srs/srs.pdf).

## Components

```
            Customers (browser / phone)            Shop staff (counter PC, phone)
                     │                                      │
                     ▼                                      ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Caddy  (HTTPS, /api → API, bots → server-rendered SEO pages,     │
   │         everything else → React app)                              │
   └──────────────────────────────────────────────────────────────────┘
          │ static files                              │ /api/v1/*
          ▼                                           ▼
 ┌──────────────────────┐                 ┌───────────────────────────┐        ┌───────────────┐
 │ apps/web  (React)    │                 │ apps/api  (FastAPI)       │──SQL──▶│ PostgreSQL 16 │
 │ website, back office │                 │ all business rules,       │        └───────────────┘
 │ POS (offline PWA),   │                 │ outbox, ledgers, auth     │──────▶ Redis (rate limits,
 │ Pay Now page         │                 └───────────────────────────┘        Celery broker)
 └──────────────────────┘                   ▲     ▲          │      │
                                            │     │          │      └──▶ Razorpay, WhatsApp provider,
                       /internal/* (X-Internal-Key)          │           2factor SMS, Shiprocket, R2 images
                                            │     │          ▼
                         ┌──────────────────┘     │   ┌────────────────────┐
                         │ apps/worker (Celery)   │   │ apps/ai-service    │──▶ Anthropic API (Claude)
                         │ schedules only         │   │ (FastAPI, port 8001)│
                         └────────────────────────┘   └────────────────────┘
                                                  │
                          outbound HTTPS only     │  (X-Tally-Agent-Key)
                         ┌────────────────────────┴───┐
                         │ apps/tally-bridge (Windows) │──XML──▶ TallyPrime on 127.0.0.1:9000
                         └─────────────────────────────┘
```

| Component | Folder | Runs as | Notes |
|---|---|---|---|
| API | `apps/api` | `uvicorn app.main:app` (port 8000) | 23 modules, 192 endpoints under `/api/v1`, OpenAPI at `/docs` |
| Web | `apps/web` | Vite dev server / static build behind Caddy | Website, back office, POS, Pay Now; English only |
| Worker | `apps/worker` | `celery -A app.celery_app worker -B` | Only calls `/api/v1/internal/*`; holds no business logic |
| AI service | `apps/ai-service` | `uvicorn app.main:app --port 8001` | Calls Claude; the API works without it |
| Tally bridge | `apps/tally-bridge` | Windows service (NSSM) next to TallyPrime | Pulls outbox, pushes vouchers, reads new Tally vouchers |
| Database | Docker `pgvector/pgvector:pg16` | | Append-only triggers on ledgers ([data-model.md](data-model.md)) |
| Web server | `infrastructure/caddy/Caddyfile` | Docker, profile `app` | Automatic HTTPS for `WEARVERSE_DOMAIN` |

## API modules

Each module lives in `apps/api/app/modules/<name>/` with `models.py`, `service.py` (rules) and `router.py`
(HTTP). Routers never hold rules; tests call services directly.

| Module | URL prefix | What it owns |
|---|---|---|
| auth | `/auth` | Staff login (phone + password), refresh, OTP, staff users, roles, manager PIN |
| catalog | `/catalog` | Products, variants, images; re-indexes the AI search index on change |
| inventory | `/inventory` | `stock_levels`, `stock_movements`, reservations, stock counts |
| customers | `/customers` | Customer records, website registration with OTP |
| pos | `/pos` | Bills, split payments, returns, cash registers, bill series, offline sync |
| khata | `/khata` | Accounts, append-only ledger, allocations, ageing, Pay Now link creation, integrity check |
| payments, pay, webhooks | `/payments`, `/pay`, `/webhooks` | Razorpay orders, public Pay Now page, signed webhooks |
| store, orders, shipping | `/store`, `/orders` | Public catalogue, checkout, tracking, customer login, SEO pages; staff order handling, Shiprocket |
| purchasing | `/purchases` | Suppliers, supplier bills, purchase orders, labels |
| employees, payroll | `/employees`, `/payroll` | Attendance, advances, salary runs and payments, own statement |
| fall_pico | `/fp` | Fall-pico jobs, workers, wages ledger, QC / rework, cost |
| notifications | `/messages` | WhatsApp/SMS jobs, templates, opt-ins, resend |
| tally | `/tally` | Outbox to Tally, inbox from Tally, mappings, sync issues, reconciliation, Mode A/B |
| reports, settings | `/reports`, `/settings` | Dashboard, sales/GST reports, alerts; business settings |
| internal | `/internal` | Scheduled jobs called by the worker |
| assist | `/ai` | Recommendations, smart/visual search, chatbot, size help, descriptions, posters, forecast, what to buy |

Shared code is in `apps/api/app/core/`: `config.py` (env), `db.py`, `errors.py` (response envelope),
`security.py` (JWT), `money.py` and `gst.py`, `outbox.py`, `sequences.py` (bill numbers), `idempotency.py`,
`ratelimit.py`, `audit.py`, `alerts.py`, `app_settings.py` (business settings with defaults).

## Design rules

1. **One source of truth.** Stock, money and order status are only ever written by the API inside one
   database transaction. The worker, AI service and Tally bridge ask the API; they never write tables.
2. **Append-only money.** Khata ledger, fall-pico wages, salary payments, stock movements and the audit log
   are insert-only (database triggers). Mistakes are fixed with a reversing entry. See ADR 0003.
3. **Outbox for side effects.** A sale writes its Tally voucher and WhatsApp message as outbox rows in the
   same transaction; workers send them later with retries and backoff. A crash never loses or doubles one.
4. **Idempotency.** POS bills, checkouts and payments carry an idempotency key; repeating a request returns
   the first result.
5. **Money in paise.** Integers only; GST is included in prices and split per line. See ADR 0006.
6. **AI is optional.** Every AI feature has a non-AI fallback, a feature switch and a shared monthly budget.
   AI never decides money, stock or order status. See [ai.md](ai.md) and ADR 0004.
7. **One business.** No tenants (ADR 0002).

Further reading: [data-model.md](data-model.md) · [flows.md](flows.md) · [ai.md](ai.md) ·
[../api/README.md](../api/README.md) · [../security.md](../security.md)
