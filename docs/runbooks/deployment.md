# Deployment

One Linux server (2 vCPU, 4 GB RAM is enough to start) runs everything with Docker Compose. TallyPrime and the
Tally bridge run on a separate Windows server (see [tally-bridge.md](tally-bridge.md)).

## What runs

`docker compose --profile app up -d --build` starts:

| Service | Image | Port | Notes |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | 5432 | Data in volume `pgdata` |
| `redis` | `redis:7-alpine` | 6379 | Broker and rate limits; no data that matters |
| `mailpit` | `axllent/mailpit` | 8025 | Test e-mail only — do not use in production |
| `api` | `apps/api` | 8000 | Runs `alembic upgrade head` on every start, then uvicorn |
| `worker` | `apps/worker` | — | Celery worker + beat |
| `ai` | `apps/ai-service` | 8001 | Needs `ANTHROPIC_API_KEY` for AI wording |
| `web` | `caddy:2-alpine` | 80, 443 | Serves `apps/web/dist`, proxies `/api`, HTTPS certificate, SEO pages for bots |

## First deployment

1. DNS: point `WEARVERSE_DOMAIN` (e.g. `shop.example.in`) at the server. Open ports 80 and 443 only.
   **Block 5432, 6379, 8000, 8001 and 8025 from the internet** (cloud firewall); compose publishes them for
   local use.
2. Copy the repository to the server and create `apps/api/.env` from `.env.example`:
   - `ENVIRONMENT=production`, `PUBLIC_WEB_URL=https://<domain>`, `CORS_ORIGINS=https://<domain>`
   - new random `JWT_SECRET`, `PAYLINK_SECRET`, `TALLY_AGENT_API_KEY`, `INTERNAL_API_KEY`
     (`openssl rand -hex 32` each)
   - live Razorpay, WhatsApp provider, 2factor, Shiprocket, R2 and Anthropic keys
   - `CUSTOMER_OTP_TEST_MODE=false`
   - change the database password in `docker-compose.yml` and `DATABASE_URL` (the default `fashionos`
     password is for local use)
3. Build the web app and start:
   ```bash
   pnpm install && pnpm build:web
   WEARVERSE_DOMAIN=shop.example.in docker compose --profile app up -d --build
   ```
4. Create the owner login and counter:
   ```bash
   docker compose exec api python -m scripts.seed --phone <owner mobile> --password '<strong password>' --pin <4-6 digits>
   ```
   (no `--demo` in production).
5. In Razorpay, set the webhook URL `https://<domain>/api/v1/webhooks/razorpay` with the same secret as
   `RAZORPAY_WEBHOOK_SECRET`. In the WhatsApp provider, set `https://<domain>/api/v1/webhooks/whatsapp`.
6. Check: on the server `curl localhost:8000/health` → `{"status":"ok",...}`; then open the website, log in to
   the back office, and open `/pos` once on the counter PC.
7. Fill Settings (shop GSTIN, size charts, FAQ, Shiprocket pickup name, AI budget) and the Tally mappings.
8. Install the Tally bridge on the Tally server.

## Updating

```bash
git pull
pnpm install && pnpm build:web
docker compose --profile app up -d --build      # api applies new migrations on start
docker compose logs -f api worker               # watch for errors
```

Take a database backup first ([backup-restore.md](backup-restore.md)). Migrations can be rolled back with
`docker compose exec api alembic downgrade -1`, but a restore is safer for data changes.

POS devices pick up the new version on the next reload; bills waiting offline still sync because the API keeps
accepting the same bill format.

## Logs and health

| What | Command / place |
|---|---|
| API and worker | `docker compose logs -f api worker` |
| Web server | `docker compose logs -f web` |
| Tally bridge | `logs\bridge.log` next to the bridge on the Windows server |
| Alerts | Back office dashboard (negative stock, Tally backlog, khata integrity, AI budget) |
| Tally state | Back office → Tally → Sync status (last heartbeat, waiting vouchers, sync issues) |
