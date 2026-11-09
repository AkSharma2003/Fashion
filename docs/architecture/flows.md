# Key flows

Each flow names the code that runs it, so a reader can follow it in the source.

## 1. Khata sale at the counter (Mode B, live POS) — T06

1. Cashier scans items in the POS (`apps/web/src/routes/pos/PosScreen.tsx`), picks the customer and puts
   part or all of the bill on khata.
2. POS sends `POST /api/v1/pos/bills` with an idempotency key (`counter + local bill number`).
3. `pos/service.create_bill` in one transaction:
   - takes prices from the server, not the POS (`PRICE_MISMATCH` otherwise);
   - checks discount against the role limit (`discount_limit_percent`); above it needs a manager PIN
     (`APPROVAL_REQUIRED`);
   - checks the khata credit limit (`CREDIT_LIMIT_EXCEEDED`) unless a manager overrides with PIN;
   - gives the next number in the series (`C1-26-000123`);
   - writes `stock_movements` (−qty) and updates `stock_levels`;
   - posts a `SALE` entry to `ledger_entries` with the new running balance;
   - creates fall-pico jobs for sarees above `fall_pico_limit_paise` (unless declined);
   - writes outbox rows: Tally sales voucher (`WV-...` reference) and a WhatsApp bill message.
4. Worker sends the message (every 10 s) and the Tally bridge picks up the voucher.
5. A repeated request with the same key returns the same bill (T04).

## 2. Offline POS

- The POS is an installable web app (`public/sw.js`, `lib/offline/db.ts`). Without internet it keeps the bill
  in IndexedDB with its key and device time, prints it, and shows it as "waiting to sync".
- `features/pos/usePosSync.ts` pushes the queue when the connection returns; the idempotency key makes retries
  safe.
- Offline khata sales are allowed up to `khata_offline_limit_percent` (80%) of the limit.
- If the shop sold the last piece offline while the website also sold it, the bill is accepted, stock goes
  negative and a `system_alerts` row tells staff to fix it.

## 3. Pay Now link (pay from home) — T10, T11, T12

1. Staff press "Send Pay Now link" (`POST /khata/accounts/{id}/paylink`) or the reminder job sends one.
2. The link is `PUBLIC_WEB_URL/pay/<token>`; only a hash of the token is stored; valid `paylink_valid_days` (7).
3. Customer opens `/pay/<token>` → `GET /pay/{token}` shows balance and recent bills (rate limited).
4. `POST /pay/{token}/start` creates a Razorpay order for the amount the customer typed (partial allowed).
5. Razorpay calls `POST /webhooks/razorpay`. The signature is checked; the event id is stored once
   (duplicates ignored). Only then is a `PAYMENT` ledger entry posted, allocated oldest bill first; extra
   becomes advance. A receipt goes out on WhatsApp and a receipt voucher to Tally.
6. Without Razorpay keys (local only) the page offers "simulate payment".

## 4. Website order — T05, T26, T28

1. `POST /store/checkout` with a cart and an idempotency key. Payment is online or COD; khata is never offered.
2. Stock is **reserved** (`stock_levels.reserved`), not deducted. The last unit can be reserved only once.
3. Online: order is `PENDING_PAYMENT` until the signed webhook, then `PAID`. Unpaid orders are released after
   `reservation_minutes` (30) by the worker (`/internal/orders/release-expired`).
4. COD: order is `CONFIRMED` straight away.
5. On payment (or COD acceptance) `orders/service.confirm` turns the reservation into a real stock
   deduction, queues the Tally sales voucher and an "order confirmed" WhatsApp message.
6. Sarees above the limit get a fall-pico job and the order waits in `FALL_PICO_IN_PROGRESS`; it cannot be
   packed before QC passes (T24). Otherwise it goes to `READY_TO_PACK`.
7. Staff move it through `PACKED → SHIPPED → DELIVERED` in Online orders. Shipping
   (`POST /orders/{id}/shipment`) books Shiprocket when no AWB is typed; if booking fails, staff type the AWB.

Order statuses: `PENDING_PAYMENT, PAID, CONFIRMED, FALL_PICO_IN_PROGRESS, READY_TO_PACK, PACKED, SHIPPED,
DELIVERED, CANCELLED, RETURNED`.

## 5. WhatsApp message — T08, T09

1. A business event calls `notifications/service.queue_message` with **facts** (amounts, bill no, link).
2. The worker calls `process_pending`. If the `message` AI feature is on and the budget allows, the AI service
   writes wording around placeholders (`{amount}`); the API fills the placeholders itself.
3. A validator checks every number in the text against the facts. Any mismatch → approved template instead
   (T08).
4. No WhatsApp opt-in → SMS and the job is flagged (T09). Quiet hours (21:00–09:00) delay reminders.
5. Delivery updates arrive on `POST /webhooks/whatsapp`.

## 6. Tally sync

**Mode A (start of rollout).** The counter keeps billing in TallyPrime. The bridge reads vouchers newer than the
last `ALTERID` and posts them to `POST /tally/inbox`. WearVerse makes bills, stock movements and khata entries
from them (T34, T35, T41). Unknown party or item → `sync_issues`, no customer message (T36). Vouchers with a
`WV-` reference are skipped (WearVerse made them).

**Mode B (after cut-over).** POS bills are made in WearVerse; vouchers flow out through the outbox:
`GET /tally/outbox/pending` → bridge builds XML → posts to Tally → `POST /tally/outbox/{id}/result`. Failures
back off; after `tally_max_attempts_before_issue` (5) they become sync issues. If vouchers wait longer than
`tally_alert_after_minutes` (30) an alert is raised.

**Parallel run.** With POS mode "parallel", POS bills are saved with `is_shadow = true` and change no stock,
khata or Tally, so they can be compared with Tally for two weeks.

**Reconciliation.** Nightly `POST /internal/tally/reconcile` compares day totals; differences show in
Tally → Reconciliation.

## 7. Salary month — T19, T20, T21

1. Supervisor marks attendance daily (P full, H half, L paid leave, A absent, W weekly off).
2. Accountant creates the run for a month (`POST /payroll/runs`): pay is worked out in half-day units;
   advance recovery is deducted.
3. Owner approves; the run is locked. Payments are recorded per employee (append-only).
4. Advances above `advance_limit_paise` need the owner (T20). Each employee sees only their own statement
   (`GET /payroll/me/statement`, T21).

## 8. Fall-pico job — T22, T23

`PENDING → ASSIGNED → IN_PROGRESS → COMPLETED → QC_PASSED → READY → HANDED_OVER`; QC can send it to `REWORK` (back to
`IN_PROGRESS`), and open jobs can be `CANCELLED`. The worker's wage is posted to `fp_worker_ledger` once, at
`QC_PASSED`; rework never pays twice. Damage or delay is recorded as an incident.

## 9. Purchase order to stock

What to buy (`GET /ai/what-to-buy`) → "Create purchase order" (`POST /purchases/orders/from-suggestions`) →
`SENT` → goods arrive → `POST /purchases/orders/{id}/receive` creates the supplier bill (`purchases`), adds stock
and queues a Tally purchase voucher. Labels: `GET /purchases/{id}/labels`.
