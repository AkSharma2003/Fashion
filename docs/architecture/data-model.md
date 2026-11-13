# Data model

PostgreSQL 16, 68 tables, managed with Alembic (`apps/api/alembic/versions`). All money columns end in
`_paise` and are integers. GST rates are stored in basis points (`gst_rate_bp`: 500 = 5%). Timestamps are
UTC; reports group by `Asia/Kolkata` date.

## Migrations

| Revision | What it adds |
|---|---|
| `874b0179b5a8` … `c6de5b9d75d0` | Earlier team migrations: core tables, roles/staff users, products, images, variants and stock, customers, khata accounts |
| `a1b2c3d4e5f6` | Phase 1 tables (catalog, stock, POS, khata, payments, orders, Tally, employees, fall-pico, messages, settings) |
| `b7c8d9e0f1a2` | Append-only triggers: `UPDATE`/`DELETE` raise an error on ledger and log tables |
| `c3d4e5f6a7b8` | Phase 2/3: purchase orders, AI search index, forecasts, customer requests, chat, AI usage |

Run `alembic upgrade head`. `alembic check` must report no drift after a model change.

## Tables by area

### Shops

| Table | Purpose |
|---|---|
| `shops` | Sethi Saree Sansar (main), Sethi Suit, Sethi Kids: code (bill prefix), GSTIN, state, address, Tally company. Stock, counters, bills, purchases and staff refer to a shop (ADR 0007) |

### Catalog and stock

| Table | Purpose |
|---|---|
| `products` | Name, category, selling price, MRP, GST rate, HSN, `fall_pico_eligible` |
| `variants` | Size / colour / price / cost per product; SKU unique |
| `barcodes` | Extra scan codes for a variant |
| `product_images` | Image object keys in R2 |
| `stock_levels` | One row per variant **per shop**: `on_hand`, `reserved` (available = on_hand − reserved) |
| `stock_movements` | **Append-only.** Every change: `quantity_delta`, `movement_type` (shop sale, online sale, returns, purchase, adjustment, count, Tally import), source, reference |
| `stock_counts` | Physical count results |

`stock_levels` can go negative only through accepted offline POS sales; that raises a `system_alerts` row.

### Shop billing

| Table | Purpose |
|---|---|
| `counters`, `bill_series` | Counter codes and the per-counter, per-financial-year bill number (`C1-26-000123`) |
| `bills` | One bill: totals, CGST/SGST/IGST split, `source` (pos / tally), `is_shadow` (parallel run), `idempotency_key` unique |
| `bill_items` | Lines with per-line taxable and tax amounts, `returned_qty`, `fall_pico_declined` |
| `bill_payments` | Split payment parts: cash / upi / card / khata |
| `bill_returns` | Return of a bill, refund mode, approver |
| `cash_registers` | Day open/close with expected vs counted cash |

### Khata (customer credit)

| Table | Purpose |
|---|---|
| `khata_accounts` | One active account per customer (partial unique index), limit, credit days, cached `balance_paise`, `last_entry_seq`, dispute and reminder flags |
| `ledger_entries` | **Append-only.** `seq` per account, `entry_type` (debits `SALE`, `OPENING`; credits `PAYMENT`, `RETURN`, `WRITE_OFF`; plus `REVERSAL` and adjustments), signed `amount_paise` (+ owed, − paid), `running_balance_paise`, `reverses_entry_id` |
| `ledger_allocations` | Which payment paid which bill (oldest first) |
| `payment_links` | Pay Now links: only the token hash is stored, expiry, active flag |

The integrity check recomputes every balance from entries and compares it with the cached balance
(`GET /khata/integrity`, nightly job). Row locks on the account keep `seq` and the running balance correct under
concurrent sales.

### Payments and website orders

| Table | Purpose |
|---|---|
| `payments` | Razorpay payments for khata or orders; `captured` only after a signed webhook |
| `webhook_events` | Unique `(provider, event_id)`: duplicate webhooks are ignored |
| `orders`, `order_items` | Website orders; `idempotency_key` unique; `reservation_expires_at` for unpaid orders |
| `order_status_logs` | Every status change |
| `shipments` | Courier, AWB, tracking, COD amount and remittance |
| `returns`, `refunds` | Website returns and gateway refunds |
| `customers`, `whatsapp_optins` | Customers and their WhatsApp consent |
| `contact_messages` | Messages from the website's Contact page (`NEW` / `DONE`) |
| `customer_addresses` | Customer address book: name, phone, address, pincode, type (Home/Work/Other), one default per customer |
| `customer_wishlist`, `customer_cart` | A signed-in customer's saved wishlist and bag; merged with guest picks at sign-in, removed from the browser at sign-out |

### Tally

| Table | Purpose |
|---|---|
| `outbox_events` | Work for Tally and messages: `reference` unique (`WV-...`), attempts, `next_attempt_at` backoff |
| `tally_inbox` | Vouchers read from Tally (Mode A), unique by Tally GUID |
| `tally_ledger_map`, `tally_item_map` | WearVerse customer/supplier/variant ↔ Tally ledger/stock item names |
| `sync_issues` | Anything that could not be matched or posted; resolved by staff |
| `reconciliation_runs` | Nightly comparison of WearVerse totals with Tally totals |

### People and fall-pico

| Table | Purpose |
|---|---|
| `staff_users`, `roles` | Logins with password and optional manager PIN |
| `employees`, `attendance` | Employees, daily status P / H / L / A / W |
| `advances`, `advance_recoveries` | Salary advances and their monthly recovery |
| `salary_runs`, `salary_lines` | Monthly run: draft → approved (locked); pay in half-day units |
| `salary_payments` | **Append-only** salary payments (reversals point to `reverses_id`) |
| `fp_workers`, `fp_worker_ledger` | Fall-pico workers and their **append-only** wage ledger |
| `fp_jobs`, `fp_job_events`, `fp_incidents`, `fp_materials` | Jobs, status history, damage/rework incidents, material spend |

### Messages, settings, audit

| Table | Purpose |
|---|---|
| `message_jobs`, `message_events`, `message_templates` | WhatsApp/SMS jobs with facts, final text and its source (ai / template), delivery events |
| `settings` | Business settings as JSON; defaults in `app/core/app_settings.py` |
| `audit_logs` | **Append-only** who changed what (old/new value, device) |
| `system_alerts` | Alerts with a dedupe key (negative stock, Tally backlog, AI budget, integrity) |
| `idempotency_keys`, `number_sequences` | Stored responses for repeated requests; order/purchase numbers |

### Phase 2 / 3 (AI and buying)

| Table | Purpose |
|---|---|
| `product_embeddings` | Search tokens and colour signature per product (rebuilt nightly and on product change) |
| `forecasts` | 7 / 30 / 90-day unit forecast per variant, confidence, basis |
| `missing_product_requests` | Products customers asked for that we do not have (empty searches, chat, staff) |
| `chat_sessions`, `chat_messages` | Chatbot history, kept `chat_retention_days` (90) |
| `ai_usage` | Tokens and cost per AI call, for the monthly budget |
| `purchase_orders`, `purchase_order_items` | Purchase orders: `DRAFT` → `SENT` → `RECEIVED` / `CANCELLED` |
| `suppliers`, `purchases`, `purchase_items` | Suppliers and supplier bills (stock-in) |

## Append-only tables

Protected by triggers from migration `b7c8d9e0f1a2` (source also in `database/policies/001_append_only.sql`):
`ledger_entries`, `ledger_allocations`, `stock_movements`, `audit_logs`, `fp_worker_ledger`, `fp_job_events`,
`salary_payments`, `advance_recoveries`, `order_status_logs`, `message_events`, `webhook_events`.

To correct a mistake, post a reversal or adjustment through the API; never edit rows by hand.
