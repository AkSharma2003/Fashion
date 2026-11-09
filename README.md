# WearVerse
## Integrated Fashion Retail Management System

### Group Details

- **Group Number:** 36

| S. No. | Name                        | Enrollment Number   |
|--------|-----------------------------|---------------------|
| 1      | Ankit Sharma                | 20252651007         |
| 2      | Shubham Gupta               | 20252651021         |
| 3      | Piyush lalchand Menghani    | 20252651039         |
| 4      | Vijay Singh                 | 20252651064         |
| 5      | Vivek Kumar Kosta           | 20252651065         |

### Project Description

WearVerse runs one fashion business from one system: one shop and one website that share **one stock**, shop
billing that keeps working offline, customer credit (**khata**) with WhatsApp bills and Pay Now links, two-way
**TallyPrime** sync, employees and payroll, and saree **fall-pico** jobs. It follows the project SRS v1.0
(written under the working name "FashionOS"; requirement IDs such as `FR-KHT-02` refer to that document).

### What is built (Phase 1)

| Area | What works | Code |
|---|---|---|
| Catalog and shared stock | Products, variants (size/colour/price/MRP), barcodes, one stock ledger (`stock_movements`), website reservations, stock count, negative-stock alerts for offline oversell | `apps/api/app/modules/catalog`, `inventory` |
| Shop billing (POS) | Installable offline web app: scan, discounts (role limits + manager PIN), split payment cash/UPI/card/khata, hold bills, print, offline queue with idempotent sync, new bill series `C1-26-000123`, returns, cash register / day close | `apps/web/src/routes/pos`, `apps/api/app/modules/pos` |
| Khata | Append-only ledger with running balance, oldest-bill-first allocation, ageing, credit limit with manager override, reversals / write-off (owner), daily integrity check, reminders (quiet hours, disputes, opt-out) | `modules/khata` |
| WhatsApp bills | Outbox → AI wording with placeholders → validator → approved template fallback → WhatsApp, SMS on failure; delivery webhooks; resend | `modules/notifications`, `apps/ai-service` |
| Pay from home | Signed 7-day Pay Now links, Razorpay order, payment confirmed only by signed webhook, duplicate webhooks ignored, receipts on WhatsApp and Tally | `modules/payments`, `pay`, `webhooks`, `apps/web/src/routes/portal` |
| Tally | Mode A (bills in TallyPrime, imported) and Mode B (POS bills pushed); outbox with unique `WV-` references and backoff; agent reads Tally by ALTERID; Sync Issues with retry; ledger/item mapping; nightly reconciliation; parallel-run mode | `modules/tally`, `apps/tally-bridge` |
| Employees and payroll | Attendance (P/H/L/A/W), monthly and daily pay, advances with limits, salary runs (draft → owner approval → locked), payments, employee's own statement | `modules/employees`, `payroll` |
| Fall-pico | Jobs created from bills / paid orders for sarees above the limit, job board, assignment, QC / rework, wages paid once, worker statement, monthly cost | `modules/fall_pico` |
| Purchasing | Suppliers, supplier bills, stock-in, labels to print, Tally purchase voucher | `modules/purchasing` |
| Website | Store API, checkout (online or COD, never khata), stock reserve and 30-minute release, order tracking, customer login and my orders, staff order handling, shipment, returns and refunds | `modules/store`, `orders` |
| Access, audit, reports | Roles (Owner, Admin, Manager, Cashier, Accountant, OnlineStaff, Supervisor, Employee), audit log, owner dashboard, sales / GST / ageing reports, settings and staff logins | `modules/auth`, `reports`, `settings` |

### Phase 2 and 3 (AI and buying intelligence)

| Feature (SRS) | What works | Runs on |
|---|---|---|
| AI-0 WhatsApp wording | AI writes words around placeholders; validator; template fallback | AI service (Claude) |
| AI-1 Recommendations | Similar, also bought, complete the look, picked for you; bestsellers fallback | API, own sales data |
| AI-2 Support chatbot | FAQ + product answers; order status only from the database and only to its owner; no discounts or khata in chat; AI disclosure; 90-day history | API + AI service |
| AI-3 Smart search | "lal silk saree under 5000" → colour, fabric, price filters (Hindi/Hinglish words); empty searches logged as customer requests | API rules + AI service for long queries |
| AI-4 Size help | Size chart per category (Settings), fit preference, past "too small / too big" returns | API |
| AI-5 Description writer | Title, description, tags from product details and photo; staff edit before saving | AI service (Claude, vision) |
| AI-6 Poster maker | Square / story / banner posters with the exact text staff type and product photos; AI suggests wording; SVG / PNG download | API template engine + AI service |
| AI-7 Visual search | Customer uploads a photo; products ranked by colour and pattern of their photos | API |
| AI-8 Demand and trend forecast | 7 / 30 / 90-day forecast per item (smoothing, weekday pattern, last year's season), confidence label, trending items and categories | API |
| AI-9 What to buy | Reorder list with quantity and budget, products customers asked for, rising categories, AI summary whose numbers are checked; one click to a purchase order | API + AI service |
| Purchase orders | Draft, send, cancel, receive into stock (creates the purchase and Tally voucher) | API |
| One sign-in | One login page for staff and customers; staff land on their role's screen; Google sign-in for customers (needs `GOOGLE_CLIENT_ID`). The web app is English only | API + Web |
| SEO | Per-page title/description/canonical/Open Graph, Product JSON-LD, sitemap.xml, robots.txt, server-rendered pages for search and link-preview bots (Caddy) | API + Caddy |
| Courier | Shiprocket booking (order + AWB) with manual AWB fallback | API |

Every AI feature has an on/off switch and shares a monthly cost limit (AI tools → AI usage). With the
AI service down or no `ANTHROPIC_API_KEY`, every feature falls back (T32): bestsellers, keyword search,
FAQ answers, simple descriptions, standard message templates.

Standard API response: `{"success": true, "data": ..., "error": null}`; errors carry `error.code`
(`CREDIT_LIMIT_EXCEEDED`, `OUT_OF_STOCK`, ...). Full API docs at `http://localhost:8000/docs`.

**To check before going live:** Tally XML field names and the debit/credit sign convention on a TallyPrime
test company; the Shiprocket pickup location name; GST slabs with the CA; size charts and FAQ text in Settings;
AI cost rates in Settings against the real Anthropic bill. Visual search compares colours and patterns, not a
deep image model; posters use templates, not an image-generation model.

**Documentation:** [docs/README.md](docs/README.md) — architecture, API, setup, runbooks (deployment, going live,
daily operations, Tally bridge, backup), staff guides, testing and security.

### Software Requirements

- Python 3.11+, Node.js 20+, pnpm, Docker and Docker Compose, Git
- FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16 (pgvector image), Redis, Celery
- React + Vite + TypeScript, Tailwind CSS
- TallyPrime with XML/HTTP access on the Tally server (for the bridge)
- Optional keys: Razorpay, WhatsApp Business API provider, 2factor.in, Anthropic (AI wording)

Without the optional keys everything still runs locally: payments are simulated, WhatsApp messages are
logged, and the standard message templates are used.

### How to Run the Project

**1. Databases**

```bash
cp .env.example apps/api/.env      # then set JWT_SECRET, PAYLINK_SECRET, TALLY_AGENT_API_KEY, INTERNAL_API_KEY
docker compose up -d               # PostgreSQL, Redis, Mailpit
```

**2. API**

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed --phone 9999999999 --password owner123 --pin 1234 --demo   # owner login + demo data
uvicorn app.main:app --reload --port 8000
```

**3. Website, back office and POS**

```bash
pnpm install
pnpm dev:web          # http://localhost:5173
```

- Website: `/` · checkout `/checkout` · order tracking `/track`
- Back office: `/login` (staff open on their role's screen, e.g. owner → `/backoffice`, cashier → `/pos`)
- POS: `/pos` (log in once; it keeps billing without internet)
- Pay Now: the link in the khata WhatsApp bill, `/pay/<token>`

**4. Worker and AI service** (each in its own terminal, same `.env` values)

```bash
cd apps/worker && pip install -r requirements.txt && celery -A app.celery_app worker -B
cd apps/ai-service && pip install -r requirements.txt && uvicorn app.main:app --port 8001
```

Or run everything in Docker: `pnpm build:web && docker compose --profile app up -d --build`
(Caddy serves the site on port 80/443 with automatic HTTPS for `WEARVERSE_DOMAIN`).

**5. Tally bridge** (on the Tally server): see [apps/tally-bridge/README.md](apps/tally-bridge/README.md).

**6. Tests**

```bash
cd apps/api && pytest       # SRS cases T01–T41, Phase 2/3 AI features (all with the AI service off), original tests
```

Two tests in `tests/test_auth_repository.py` need the PostgreSQL from step 1.

### Going live (short version)

1. Start in **Mode A** (counter keeps billing in TallyPrime; WearVerse imports). POS runs as a **parallel run**:
   bills are saved for comparison only and change no stock, khata or Tally.
2. After two clean weeks (Tally → Reconciliation shows no differences), the owner switches to **Mode B** in
   Tally → Sync status. The POS becomes live and the new bill series starts.
3. Rollback: switch back to Mode A; nothing is lost because every voucher waits in the outbox.
