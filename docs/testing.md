# Testing

## Run

```bash
cd apps/api && pytest                 # 126 tests on SQLite (fast)
# Same tests on PostgreSQL (catches column lengths and SQL that SQLite lets through) — do this before a release:
docker compose exec -T db psql -U fashionos -d postgres -c "CREATE DATABASE wearverse_test OWNER fashionos;"
TEST_DATABASE_URL=postgresql+psycopg://fashionos:fashionos@localhost:5432/wearverse_test pytest
sh tests/e2e/run.sh                   # one full shop day end to end on a fresh throwaway database (32 steps)
cd apps/web && npx tsc -p tsconfig.app.json --noEmit && npx vite build
```

Tests use an in-memory stand-in for Redis (`tests/conftest.py`), so they never depend on or fill a real Redis.

## SRS test cases (section 13)

| ID | Case | Automated test | Status |
|---|---|---|---|
| T01 | 3-item cash bill → stock down, Tally voucher | `test_T01_cash_bill_deducts_stock_and_queues_tally` | automated |
| T02 | Split payment cash + UPI + khata | `test_pos_bill_over_http_and_khata_ledger` covers khata part; no test of a three-way split | **manual** |
| T03 | Discount above role limit → manager PIN | `test_T03_discount_above_role_limit_needs_manager_pin` | automated |
| T04 | Offline bills synced once | `test_T04_same_idempotency_key_creates_one_bill` (server side) | automated + manual on a real device |
| T05 | Last unit at shop and online together | `test_T05_last_unit_can_be_reserved_only_once`, `test_offline_oversell_is_accepted_with_alert` | automated |
| T06 | Khata sale → ledger + WhatsApp | `test_T06_khata_sale_ledger_and_whatsapp` | automated |
| T07 | Over limit → blocked, manager override | `test_T07_credit_over_limit_blocked_then_manager_override` | automated |
| T08 | AI text with wrong amount → template | `test_T08_ai_text_with_wrong_amount_falls_back_to_template` | automated |
| T09 | No opt-in → SMS and flag | `test_T09_no_optin_sends_sms_and_flags` | automated |
| T10, T11 | Partial Pay Now payment; duplicate webhook | `test_T10_T11_pay_now_partial_payment_and_duplicate_webhook` | automated |
| T12 | Expired link denied | `test_T12_expired_link_is_denied` | automated |
| T13 | Ledger edit denied; reversal | `test_T13_reversal_keeps_both_entries_and_fixes_balance` (trigger itself: PostgreSQL only) | automated + manual on PostgreSQL |
| T14 | Integrity check finds tampered balance | `test_T14_integrity_check_reports_tampered_balance` | automated |
| T15 | Tally closed, 20 bills, Tally opened | — | **manual** (test company) |
| T16 | Sale entered in Tally → stock drops | covered by `test_T34_T35_T41_khata_sale_from_tally` (import); timing is manual | automated + manual |
| T17 | Deliberate mismatch → reconciliation lists it | — | **manual** (staging) |
| T18 | Return of a khata bill | `test_T18_return_of_khata_bill_reduces_balance` | automated |
| T19 | Payroll example from the SRS | `test_T19_payroll_example_from_srs`, `test_half_days_count_as_half` | automated |
| T20 | Advance above limit → owner | `test_T20_advance_above_limit_needs_owner` | automated |
| T21 | Salary privacy | `test_T21_salary_is_private` | automated |
| T22 | Fall-pico at ₹1,000 vs ₹1,001 | `test_T22_fall_pico_only_above_limit`, `test_fall_pico_declined_at_counter` | automated |
| T23 | Rework not paid twice | `test_T23_rework_is_not_paid_twice` | automated |
| T24 | Online saree not packed before QC | `test_T24_online_saree_cannot_be_packed_before_qc` | automated |
| T25 | UPI order success end to end | — | **manual** (Razorpay test mode) |
| T26 | Retry / double click → one order, one charge | `test_T26_same_checkout_key_is_one_order_and_paid_once` | automated |
| T27 | COD remittance matches courier report | — | **manual** |
| T28 | No khata online | `test_T28_online_checkout_has_no_khata` | automated |
| T29 | Cashier write-off → 403 | `test_T29_cashier_cannot_write_off` | automated |
| T30 | Full purchase on a 360 px phone | — | **manual** (browser) |
| T31 | Load test, errors under 1% | — | **manual** (`tests/load` is empty) |
| T32 | AI service off → everything works | `test_T32_chat_works_with_ai_off` and all of `test_ai_phase2_3.py` | automated |
| T33 | Chatbot refuses other orders / discounts | `test_T33_chatbot_refuses_other_orders_and_discounts` | automated |
| T34, T35, T41 | Mode A: sale / khata bill / saree from Tally | `test_T34_T35_T41_khata_sale_from_tally`, `test_vouchers_created_by_wearverse_are_skipped` | automated |
| T36 | Unmatched party → Sync issues, no message | `test_T36_unmatched_party_goes_to_sync_issues_without_message` | automated |
| T37 | New bill series in Mode B | `test_bill_series_financial_year` (format and order) | automated + manual cut-over |
| T38 | Tally server restarted | — | **manual** (Windows server) |
| T39 | Tally unreachable over 30 min → alert | backlog check exists; no automated test | **manual** |
| T40 | Paper bill book during outage | — | **manual** (process) |

**Manual before go-live:** T02, T15, T17, T25, T27, T30, T31, T38, T39, T40, and the on-device / timing parts of
T04, T13, T16, T37. Record results (date, who, pass/fail, notes) in the go-live checklist
([runbooks/going-live.md](runbooks/going-live.md)).

## Not yet covered

- No browser (end-to-end) tests; `tests/e2e`, `tests/load`, `tests/offline-sync`, `tests/tally-sync`,
  `tests/contracts` at the repo root are empty placeholders.
- The AI service is tested only against a local stub of the Messages API, not with a real key.
- The Tally bridge XML is checked by its own code paths only; it must be verified on a TallyPrime test company.

## Writing a test

Use `tests/wv_fixtures.py`: fixtures `db` (SQLite session) and `client` (test client), and helpers
`make_user(db, role, pin=...)`, `auth(user)` (bearer header), `make_variant(db, price=..., qty=...)`,
`make_khata_customer(db, limit=...)`. Name SRS tests `test_Txx_<what>` so this table stays easy to update.
