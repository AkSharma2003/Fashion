# Troubleshooting

Start with the back-office dashboard alerts and `docker compose logs -f api worker`.

## Counter (POS)

| Symptom | Cause | Fix |
|---|---|---|
| "Offline — bills saved" banner | No internet or API down | Keep billing; bills sync by themselves. Check `curl localhost:8000/health` on the server |
| Bill stuck as "waiting to sync" after internet is back | API rejected it (e.g. price changed, approval needed) | Open the POS sync list; the reason is shown. Fix and resend; the idempotency key prevents a double bill |
| `APPROVAL_REQUIRED` | Discount or credit above the role limit | Manager enters PIN |
| `CREDIT_LIMIT_EXCEEDED` | Khata limit reached | Take part payment, or manager overrides with PIN, or raise the limit in Khata |
| `POS_OFF` | POS mode is off for the current Tally mode | Tally → Sync status: POS parallel (Mode A) or live (Mode B) |
| Cannot close register (`BILLS_NOT_SYNCED`) | Offline bills still on a device | Bring that device online until it shows all synced |
| Negative stock alert | Last piece sold offline and online at the same time | Count the item; adjust stock; contact the online customer if needed |

## Khata and payments

| Symptom | Cause | Fix |
|---|---|---|
| Customer paid on Pay Now but balance did not change | Webhook not received | Razorpay dashboard → Webhooks → delivery log; URL `https://<domain>/api/v1/webhooks/razorpay`, secret matches `RAZORPAY_WEBHOOK_SECRET`. Replay the event; duplicates are ignored |
| Pay Now link "expired" | Older than 7 days | Send a new link |
| Integrity alert | Cached balance differs from the ledger | Do not edit tables. Developer: compare `GET /khata/integrity` output; the ledger is the truth |
| Wrong entry posted | Human error | Owner posts a reversal; both entries stay visible (T13) |

## WhatsApp and SMS

| Symptom | Cause | Fix |
|---|---|---|
| Messages "logged" but not sent | No WhatsApp provider keys | Set `WHATSAPP_*` in `.env`, restart api and worker |
| Messages queued, none sent | Worker down, or quiet hours for reminders | `docker compose ps worker`; quiet hours are 21:00–09:00 |
| SMS sent instead of WhatsApp, job flagged | Customer has no WhatsApp opt-in | Ask the customer; the opt-in is the "agreed to get bills on WhatsApp" box when opening the khata account (API: `POST /messages/optins`) |
| Failed message | Provider error | Khata → account → WhatsApp messages → Resend |

## Website

| Symptom | Cause | Fix |
|---|---|---|
| `OUT_OF_STOCK` at checkout | Stock reserved by another cart or sold in the shop | Normal; reservation is released after 30 min if unpaid |
| Order stays `PENDING_PAYMENT` though customer paid | Webhook missing | As for Pay Now above |
| Cannot pack saree order (`FALL_PICO_PENDING`) | Fall-pico QC not passed | Finish the job in Fall-pico |
| `AWB_REQUIRED` | Shiprocket not configured or booking failed | Book in the Shiprocket panel and type the AWB; check `shiprocket_pickup_location` |
| Product link preview has no picture on WhatsApp | Product has no image, or bot not reaching Caddy | Add an image; check the `@bot_product` rule in the Caddyfile |

## AI features

| Symptom | Cause | Fix |
|---|---|---|
| Everything works but answers look plain | AI is falling back | Check `ANTHROPIC_API_KEY` on the ai service, `docker compose logs ai`, AI tools → AI usage (source "fallback") |
| `FEATURE_OFF` | Feature switched off | Settings → `ai_features` |
| AI stopped mid-month | Budget used up (alert raised) | Raise `ai_monthly_budget_paise` or wait for next month |
| New product not found by search / photo search | Index not refreshed | AI tools → AI usage → Rebuild search index (also nightly) |

## Tally

See [tally-bridge.md](tally-bridge.md).

## Developer

| Symptom | Fix |
|---|---|
| `Table ... is append-only` error | Code tried to UPDATE/DELETE a ledger row. Post a reversing entry instead |
| `alembic check` shows operations | Model and migration differ; make a new migration |
| 409 `DUPLICATE` | A unique value (SKU, phone, reference) already exists |
| Worker logs 401 from `/internal` | `INTERNAL_API_KEY` differs between api and worker |
