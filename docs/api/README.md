# API guide

Base URL: `http://localhost:8000/api/v1` (production: `https://<WEARVERSE_DOMAIN>/api/v1`, proxied by Caddy).
Interactive docs with every field: `http://localhost:8000/docs`. Full list of 175 operations:
[endpoints.md](endpoints.md) (generated from the code).

## Response format

Every endpoint returns the same envelope (SRS 8.1):

```json
{ "success": true, "data": { "...": "..." }, "error": null }
```

On failure:

```json
{
  "success": false,
  "data": null,
  "error": { "code": "CREDIT_LIMIT_EXCEEDED", "message": "Credit limit is ₹10,000.00; this bill would make the balance ₹10,450.00." },
  "detail": "Credit limit is ₹10,000.00; ..."
}
```

`detail` repeats the message for older screens. Validation errors (422) also carry `errors` with FastAPI's
field list.

## Error codes

| Code | HTTP | When |
|---|---|---|
| `VALIDATION_ERROR` | 400/422 | Bad or missing input |
| `UNAUTHORIZED` | 401 | No token, expired token |
| `FORBIDDEN` | 403 | Role not allowed |
| `NOT_FOUND` | 404 | Record does not exist |
| `DUPLICATE` | 409 | Unique value already used |
| `INVALID_STATUS` | 422 | Status change not allowed (order, PO, fall-pico job, salary run) |
| `LOCKED` | 409/422 | Approved salary run, closed register |
| `OUT_OF_STOCK` | 409 | Website checkout cannot reserve the quantity |
| `PRICE_MISMATCH` | 422 | POS price differs from the server price |
| `APPROVAL_REQUIRED` / `APPROVAL_INVALID` | 422 | Discount, credit override, advance or return needs a manager / owner PIN |
| `CREDIT_LIMIT_EXCEEDED` | 422 | Khata balance would go over the limit |
| `NO_KHATA` | 422 | Customer has no active khata account |
| `RETURN_WINDOW` | 422 | Return after `return_days` |
| `FALL_PICO_PENDING` | 422 | Order with fall-pico not passed QC cannot be packed |
| `LINK_INVALID` / `LINK_EXPIRED` | 404/410 | Pay Now link wrong or older than 7 days |
| `POS_OFF` | 422 | POS billing not allowed in the current Tally mode |
| `BILLS_NOT_SYNCED` | 422 | Register close / mode switch with offline bills still waiting |
| `AWB_REQUIRED` | 422 | Courier booking failed; type the AWB |
| `FEATURE_OFF` | 422 | AI feature switched off in Settings |
| `RATE_LIMITED` | 429 | Too many requests |

## Authentication

| Who | How | Header |
|---|---|---|
| Staff or customer (one login page) | `POST /auth/sign-in` with phone/e-mail + password → `kind: staff` (with `role`, access + refresh tokens) or `kind: customer` (customer token) | `Authorization: Bearer <token>` |
| Customer with Google | `POST /auth/google` with the Google ID token (verified with Google; new users add a mobile number once); `GET /auth/google/config` tells the page whether it is on | `Authorization: Bearer <customer token>` |
| Staff (older screens) | `POST /auth/login` with phone + password → access token (30 min) + refresh token (7 days); `POST /auth/refresh` | `Authorization: Bearer <access>` |
| Customer (website) | `POST /store/auth/login` (or OTP register via `/customers/customers/website/*`) → customer token (7 days) | `Authorization: Bearer <customer token>` |
| Tally bridge | Shared key `TALLY_AGENT_API_KEY` | `X-Tally-Agent-Key` |
| Worker | Shared key `INTERNAL_API_KEY` for `/internal/*` | `X-Internal-Key` |
| Razorpay / WhatsApp webhooks | Signature checked with the webhook secret | provider's signature header |
| Pay Now page | The link token in the URL (only its hash is stored) | — |

Public without login: `/store/*` catalogue, search, checkout, tracking (`order_no` + phone), SEO pages,
`/pay/{token}`, `/ai/recommendations`, `/ai/search`, `/ai/visual-search`, `/ai/chat`, `/ai/size*`.

### Roles

`Owner`, `Admin`, `Manager`, `Cashier`, `Accountant`, `OnlineStaff`, `Supervisor`, `Employee`. Owner and Admin
pass every role check. The main rules:

| Area | Allowed |
|---|---|
| POS billing, registers | Cashier, Manager |
| Khata accounts, payments | Cashier, Manager, Accountant; write-off and reversal: Owner only (T29) |
| Products, stock | Manager, Cashier, OnlineStaff (catalog writes need a staff login) |
| Online orders, shipments | OnlineStaff, Manager |
| Fall-pico | Supervisor, Manager |
| Purchasing, AI buying tools | Manager, Accountant |
| Employees, attendance, advances | Manager, Accountant |
| Payroll runs | Accountant prepares; Owner approves |
| Tally, reports | Accountant |
| Settings, staff users | Owner / Admin |
| Own statement | Every staff user (`/payroll/me/statement`) |

Manager PIN: actions above a limit take `approval.pin` (or `approval_pin`); the API looks for an active
Manager / Owner / Admin with that PIN and records who approved.

## Idempotency

Send a unique key with anything that creates money or stock:

- POS bill: `idempotency_key` in the body (POS uses `counter-localNumber`).
- POS return: `idempotency_key` in the body.
- Website checkout: `idempotency_key` in the body (min 8 characters).

The same key returns the first result and creates nothing new (T04, T26).

## Money

All amounts are **integers in paise** (`₹1,250.50` = `125050`). Prices include GST. GST rate fields are basis
points (`500` = 5%). The server calculates prices and tax; values sent by a device are only compared.

## Rate limits (per IP, per minute)

Customer login 10 · checkout 20 · Pay Now open 30 · Pay Now start 10 · smart search 60 · visual search 10 ·
chat 20. If Redis is down, limits are skipped (logged) rather than blocking sales.

## Example: push a khata bill from the POS

```http
POST /api/v1/pos/bills
Authorization: Bearer <cashier token>
Content-Type: application/json

{
  "idempotency_key": "C1-000457",
  "counter_id": "C1",
  "customer_id": "3c0e1c9e-...",
  "items": [
    { "variant_id": "9b1d...", "qty": 1, "price": 349900, "discount_paise": 0 },
    { "variant_id": "77aa...", "qty": 2, "price": 59900 }
  ],
  "payments": [
    { "mode": "CASH", "amount": 100000 },
    { "mode": "KHATA", "amount": 369700 }
  ],
  "created_at_device": "2026-11-09T11:42:10+05:30"
}
```

Response `data` contains the bill with its number (`C1-26-000457`), GST split, payments, the new khata
balance, and any fall-pico job tags. Discount above the cashier's limit returns `APPROVAL_REQUIRED`; send again
with `"approval": {"pin": "1234", "reason": "regular customer"}`.

## Keeping these docs current

After adding or changing endpoints run `cd apps/api && python -m scripts.gen_api_docs` and commit
`docs/api/endpoints.md` with the code.
