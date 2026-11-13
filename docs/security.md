# Security

What protects the shop's money, stock and customer data, and what must be set up before going live.

## Controls in the code

| Risk | Control | Where |
|---|---|---|
| Stolen or guessed passwords | Passwords and manager PINs hashed with `pwdlib` (`PasswordHash.recommended()`, Argon2); login, OTP and checkout rate limited | `app/core/security.py`, `app/core/ratelimit.py` |
| Long-lived sessions | Staff access token 30 min, refresh 7 days; customer token 7 days; tokens signed with `JWT_SECRET` | `app/core/security.py` |
| Staff doing more than their job | Role check on every staff endpoint; Owner-only write-off, reversal, salary approval, settings; manager PIN above limits, approver recorded | `modules/auth/dependencies.py` |
| Changing history to hide fraud | Ledgers, stock movements, wages, salary payments and audit log are append-only (database triggers); corrections are reversing entries; daily khata integrity check | migration `b7c8d9e0f1a2` |
| Who changed what | `audit_logs` with old/new values and device for settings, approvals, reversals, mode changes | `app/core/audit.py` |
| Fake payment confirmations | Payment counted only after a Razorpay webhook with a valid HMAC-SHA256 signature; event ids stored once | `integrations/razorpay`, `modules/webhooks` |
| Fake WhatsApp delivery updates | Signed webhooks; unsigned accepted only when `ENVIRONMENT=local` | `integrations/whatsapp` |
| Guessable Pay Now links | Random token; only `sha256(secret:token)` stored; 7-day expiry; can be deactivated; rate limited | `modules/payments/service.py` |
| Someone else's order or balance | Order tracking needs order number + mobile; chatbot shows an order only to its owner and never shows khata; employees see only their own statement | `store`, `assist/chat.py`, `payroll` |
| Tally port exposed | Bridge makes outbound HTTPS only; Tally's port 9000 stays on 127.0.0.1; agent uses a shared key compared in constant time | `apps/tally-bridge`, `modules/tally/router.py` |
| Worker endpoints called from outside | `/internal/*` needs `X-Internal-Key`, compared in constant time | `modules/internal/router.py` |
| Prices changed on a device | Server decides price and tax; device values are only compared | `pos/service.py` |
| Double charges or double bills | Idempotency keys on bills, returns, checkout; unique `WV-` references to Tally | `pos`, `orders`, `tally` |
| Data sent to the AI provider | Only product facts, FAQ and placeholder names; no phone numbers, balances or salaries; feature switches and budget | `assist/gateway.py`, [architecture/ai.md](architecture/ai.md) |
| Secrets inside Docker images | `.dockerignore` in api, worker and ai-service keeps `.env`, `.venv`, tests and media out of images | `apps/*/.dockerignore` |
| Dodging rate limits with a fake IP | The limiter uses the last `X-Forwarded-For` entry (added by Caddy), not the first one the client can set | `app/core/ratelimit.py` |
| Script in product text on SEO pages | JSON-LD escaped (`</` → `<\/`), HTML escaped | `modules/store/router.py` |

## Must do before going live

1. New random values for `JWT_SECRET`, `PAYLINK_SECRET`, `TALLY_AGENT_API_KEY`, `INTERNAL_API_KEY`; keep them out
   of git (only `.env.example` is committed).
2. `ENVIRONMENT=production` (turns off simulated payments and unsigned webhooks), `CUSTOMER_OTP_TEST_MODE=false`.
3. Change the default database password (`fashionos`) in `docker-compose.yml` and `DATABASE_URL`.
4. Firewall: only ports 80 and 443 open on the server. Compose publishes 5432, 6379, 8000, 8001, 8025 for local
   use; block them or remove those `ports:` lines in production. Do not run Mailpit in production.
5. `CORS_ORIGINS` = the real site only.
6. Owner and manager PINs: different from passwords, not `1234`.
7. Remove staff logins on the day someone leaves (Settings → Staff logins → inactive).
8. Backups encrypted and stored off the server ([runbooks/backup-restore.md](runbooks/backup-restore.md)).
9. Razorpay and WhatsApp webhook secrets set in both the provider panel and `.env`.

## Personal data

Stored: customer name, mobile, e-mail, address (orders), khata history, WhatsApp opt-in; employee name, phone,
pay and attendance. Chat history is deleted after 90 days. Customers who withdraw WhatsApp consent stop getting
messages (opt-out recorded). There is no automatic "delete my data" flow yet; handle such requests manually
without deleting ledger entries (bills and payments must be kept for tax law).

## Reporting a problem

Tell the owner and the developer on duty the same day. Rotate any key that may have leaked (change it in `.env`
and the provider panel, restart the services).
