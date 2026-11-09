# WearVerse documentation

Rule: requirements live in the SRS. Change the SRS first, then these docs, then the code.

## Requirements and reports

- **SRS v1.0** — [srs/srs.pdf](srs/srs.pdf) (source `srs/srs.tex`; written under the working name "FashionOS").
  Online copy: https://claude.ai/artifact/2BkZRx59AKh5DDM9pdFZnA
- **Project report** (CS545 lab experiments) — [projectReport/p.pdf](projectReport/p.pdf)
- Older "Complete Project Documentation": https://claude.ai/code/artifact/02596e8d-8abb-461e-9271-fd43ae0ab3fb
  (written before the stack was fixed; it still mentions NestJS / Next.js. Follow the ADRs below.)

## For developers

| Document | What is in it |
|---|---|
| [setup/local-development.md](setup/local-development.md) | Run everything locally, tests, adding a module, code rules |
| [setup/configuration.md](setup/configuration.md) | Every environment variable and business setting with defaults |
| [architecture/overview.md](architecture/overview.md) | Components, modules, design rules |
| [architecture/data-model.md](architecture/data-model.md) | Tables by area, migrations, append-only tables |
| [architecture/flows.md](architecture/flows.md) | POS khata sale, offline POS, Pay Now, website order, WhatsApp, Tally, salary, fall-pico, purchasing |
| [architecture/ai.md](architecture/ai.md) | AI features, gateway, fallbacks, budget, privacy |
| [api/README.md](api/README.md) | Response format, error codes, auth, roles, idempotency, example |
| [api/endpoints.md](api/endpoints.md) | All 178 endpoints (generated: `python -m scripts.gen_api_docs`) |
| [testing.md](testing.md) | Test suites and SRS test cases T01–T41: automated vs manual |
| [security.md](security.md) | Controls in the code and the go-live security checklist |

## For running the shop

| Document | What is in it |
|---|---|
| [runbooks/deployment.md](runbooks/deployment.md) | Server setup, first deployment, updates, logs |
| [runbooks/going-live.md](runbooks/going-live.md) | Checks before day one, Mode A + parallel run, switch to Mode B, rollback |
| [runbooks/daily-operations.md](runbooks/daily-operations.md) | Automatic jobs, opening, closing, accountant's morning, monthly tasks |
| [runbooks/tally-bridge.md](runbooks/tally-bridge.md) | Install, checks and fixes for the Tally bridge |
| [runbooks/backup-restore.md](runbooks/backup-restore.md) | Nightly backup, restore, restore test |
| [runbooks/troubleshooting.md](runbooks/troubleshooting.md) | Symptom → cause → fix for POS, khata, messages, website, AI |

## For staff

| Document | Who |
|---|---|
| [user-guide/pos-cashier.md](user-guide/pos-cashier.md) | Cashiers |
| [user-guide/back-office.md](user-guide/back-office.md) | Owner, manager, accountant, online staff, supervisor |
| [user-guide/website-customers.md](user-guide/website-customers.md) | Online staff helping customers |

## Decisions (ADRs)

| ADR | Decision |
|---|---|
| [0001](adr/0001-stack.md) | FastAPI + PostgreSQL + Celery + React/Vite |
| [0002](adr/0002-own-business-not-saas.md) | One business, not a multi-tenant SaaS |
| [0003](adr/0003-outbox-offline-idempotency.md) | Outbox, offline POS, idempotency, append-only ledgers |
| [0004](adr/0004-ai-gateway-and-fallbacks.md) | AI through one gateway, always with a fallback |
| [0005](adr/0005-seo-dynamic-rendering.md) | SEO with server-rendered pages for bots |
| [0006](adr/0006-money-in-paise-gst-inclusive.md) | Money in paise, prices include GST |
