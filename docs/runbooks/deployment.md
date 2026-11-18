# Deployment

One Linux server (2 vCPU, 4 GB RAM is enough to start) runs everything with Docker Compose. TallyPrime and the
Tally bridge run on a separate Windows server (see [tally-bridge.md](tally-bridge.md)).

## What runs

Production uses [`docker-compose.prod.yml`](../../docker-compose.prod.yml) (the plain `docker-compose.yml` is for
local development). It starts:

| Service | Image | Port | Notes |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | internal | Data in volume `pgdata`; password from `POSTGRES_PASSWORD` |
| `redis` | `redis:7-alpine` | internal | Broker and rate limits; password from `REDIS_PASSWORD` |
| `api` | `apps/api` | internal | Runs `alembic upgrade head` on every start, then uvicorn (`API_WORKERS`, default 2) |
| `worker` | `apps/worker` | — | Celery worker + beat — keep exactly one |
| `ai` | `apps/ai-service` | internal | Needs `ANTHROPIC_API_KEY` for AI wording |
| `web` | `caddy:2-alpine` | 80, 443 | Serves `apps/web/dist`, proxies `/api`, HTTPS certificate, SEO pages for bots |

## First deployment

1. DNS: point `WEARVERSE_DOMAIN` (e.g. `shop.example.in`) at the server. Open ports 80 and 443 only.
   The production compose file publishes only 80/443; keep the cloud firewall closed for everything else.
2. Copy the repository to the server and create `apps/api/.env` from `.env.example`:
   - `ENVIRONMENT=production`, `PUBLIC_WEB_URL=https://<domain>`, `CORS_ORIGINS=https://<domain>`
   - new random `JWT_SECRET`, `PAYLINK_SECRET`, `TALLY_AGENT_API_KEY`, `INTERNAL_API_KEY`
     (`openssl rand -hex 32` each)
   - live Razorpay, WhatsApp provider, 2factor, Shiprocket, R2 and Anthropic keys
   - `CUSTOMER_OTP_TEST_MODE=false`
   - real SMTP: `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_START_TLS=true`, user/password, `SMTP_FROM_EMAIL` on your domain
   - `POSTGRES_PASSWORD`, `REDIS_PASSWORD` (`openssl rand -hex 32`), `WEARVERSE_DOMAIN=<domain>`

   With `ENVIRONMENT=production` the API **refuses to start** and lists every missing or unsafe value
   (`docker compose -f docker-compose.prod.yml logs api`). Fix them all before going on.
3. Build the web app and start:
   ```bash
   pnpm install && pnpm build:web
   docker compose -f docker-compose.prod.yml --env-file apps/api/.env up -d --build
   ```
4. Create the owner login and counter:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file apps/api/.env exec api python -m scripts.seed --phone <owner mobile> --password '<strong password>' --pin <4-6 digits>
   ```
   (no `--demo` in production).
5. In Razorpay, set the webhook URL `https://<domain>/api/v1/webhooks/razorpay` with the same secret as
   `RAZORPAY_WEBHOOK_SECRET`. In the WhatsApp provider, set `https://<domain>/api/v1/webhooks/whatsapp`.
6. Check: `docker compose -f docker-compose.prod.yml --env-file apps/api/.env ps` shows `api` as `healthy`; then open the website, log in to
   the back office, and open `/pos` once on the counter PC.
7. Fill Settings (shop GSTIN, size charts, FAQ, Shiprocket pickup name, AI budget) and the Tally mappings.
8. Install the Tally bridge on the Tally server.

## Updating

```bash
git pull
pnpm install && pnpm build:web
export COMPOSE_FILE=docker-compose.prod.yml COMPOSE_ENV_FILES=apps/api/.env
docker compose up -d --build                    # api applies new migrations on start
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
