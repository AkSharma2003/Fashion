# Configuration

Two kinds of configuration:

1. **Environment variables** — secrets and addresses. Set per machine in `apps/api/.env` (template:
   `.env.example`). The worker and AI service read the same names. Never commit real values.
2. **Business settings** — shop rules the owner can change in Back office → Settings
   (`GET/PATCH /api/v1/settings`). Stored in the `settings` table; defaults in
   `apps/api/app/core/app_settings.py`. Every change is in the audit log.

## Environment variables

| Variable | Needed | Meaning |
|---|---|---|
| `ENVIRONMENT` | yes | `local`, `dev`, `staging`, `production`. Simulated payments only work in `local` |
| `PUBLIC_WEB_URL` | yes | Base of Pay Now links in WhatsApp messages |
| `CORS_ORIGINS` | yes | Comma-separated web origins allowed to call the API |
| `DATABASE_URL` | yes | `postgresql+psycopg://user:pass@host:5432/db` |
| `REDIS_URL` | yes | Celery broker and rate limits |
| `JWT_SECRET` | yes | Signs staff and customer tokens (`openssl rand -hex 32`) |
| `PAYLINK_SECRET` | yes | Signs Pay Now link tokens |
| `TALLY_AGENT_API_KEY` | Tally | Same value in the bridge's `config/tally-bridge.local.yaml` |
| `INTERNAL_API_KEY` | worker | Worker → `/api/v1/internal/*` |
| `API_INTERNAL_URL` | worker | Where the worker finds the API, e.g. `http://api:8000/api/v1/internal` |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | live payments | Empty = simulated payments (local only) |
| `WHATSAPP_PROVIDER_URL`, `WHATSAPP_API_KEY`, `WHATSAPP_WEBHOOK_SECRET` | live WhatsApp | Empty = messages are only logged |
| `TWOFACTOR_API_KEY` | SMS / OTP | 2factor.in |
| `CUSTOMER_OTP_TEST_MODE` | local | `true` = SMS is only logged, not sent (OTP still goes by e-mail); must be `false` in production |
| `GOOGLE_CLIENT_ID` | Google sign-in | OAuth Web client id (Google Cloud console). Empty = Google button shows "not set up" |
| `SHIPROCKET_EMAIL`, `SHIPROCKET_PASSWORD` | courier | Empty = staff type AWB numbers |
| `IMAGE_STORAGE_*` | images | Cloudflare R2 (S3 compatible) bucket, endpoint, keys, public URL, max size |
| `AI_SERVICE_URL` | AI | Where the API finds the AI service (`http://localhost:8001`) |
| `ANTHROPIC_API_KEY` | AI | Set on the AI service. Empty = all AI features use fallbacks |
| `AI_MODEL_TEXT` | AI | Claude model id, default `claude-opus-5-5` |
| `WEARVERSE_DOMAIN` | production | Domain Caddy gets an HTTPS certificate for |

## Business settings

| Key | Default | Meaning |
|---|---|---|
| `shop_name`, `shop_gstin`, `shop_state_code` | WearVerse, empty | Shop details for bills. Tax is split CGST + SGST; IGST for other-state online orders is not calculated yet |
| `tally_mode` | `A` | `A`: bills in Tally, imported. `B`: WearVerse POS live, vouchers pushed |
| `tally_cutover_date` | none | Date Mode B started |
| `tally_working_hours` | 00:00–23:59 | When the bridge is expected to be online |
| `tally_alert_after_minutes` | 30 | Alert when vouchers wait longer |
| `tally_max_attempts_before_issue` | 5 | Failed attempts before a voucher becomes a sync issue |
| `fall_pico_limit_paise` | 100000 (₹1,000) | Sarees above this price get a free fall-pico job |
| `fall_pico_default_days` | 3 | Promised days for a job |
| `gst_slabs` | 5% up to ₹2,500 per piece, 18% above | **Confirm with the CA** |
| `discount_limit_percent` | Cashier 5, Manager 20, Owner/Admin 100 | Above this needs a manager PIN |
| `khata_default_limit_paise` | 1000000 (₹10,000) | Credit limit for new accounts |
| `khata_default_credit_days` | 30 | Days before a bill is due |
| `khata_offline_limit_percent` | 80 | Share of the limit the POS may use offline |
| `reminder_days_after_bill` | 7, 15, 30 | Reminder days after a khata bill |
| `reminder_weekly_after_due` | true | Weekly reminders once overdue |
| `quiet_hours` | 21:00–09:00 | No reminders in this window |
| `paylink_valid_days` | 7 | Pay Now link lifetime |
| `reservation_minutes` | 30 | Unpaid website order holds stock this long |
| `return_days` | 7 | Return window |
| `shipping_fee_paise`, `free_shipping_above_paise` | 0, 0 | Website shipping charge |
| `shiprocket_pickup_location` | `Primary` | Must match the pickup name in the Shiprocket panel |
| `shiprocket_package` | 30×25×4 cm, 0.6 kg | Default parcel size |
| `weekly_off_paid` | true | Weekly off counts as paid |
| `advance_limit_paise` | 1000000 (₹10,000) | Advance above this needs the owner |
| `ai_features` | all on | Switch per AI feature |
| `ai_monthly_budget_paise` | 500000 (₹5,000) | Monthly AI limit |
| `ai_cost_paise_per_mtok` | input 34000, output 170000 | Estimated cost per million tokens, for the limit. Check against the Anthropic bill |
| `chat_retention_days` | 90 | Chat history kept |
| `size_charts` | samples for Suits, Kids … | Size chart per category (cm) |
| `complete_the_look` | Sarees → Blouse, Petticoat, Jewellery … | Which categories go together |
| `faq` | delivery, returns, COD … | Chatbot answers: `q` keywords, `a` answer |

Values marked "confirm" or "estimate" are assumptions from the SRS and must be checked before going live
([../runbooks/going-live.md](../runbooks/going-live.md)).
