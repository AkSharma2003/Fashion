# Going live

The shop must keep selling every day of the rollout (SRS 3.18). WearVerse is switched on in steps, and every
step can be undone.

## Before day one: checks that need a person

| # | Check | Who | Where |
|---|---|---|---|
| 1 | Tally XML field names and debit/credit sign on a **test company** | Accountant + developer | `apps/tally-bridge` README, Tally → Sync issues |
| 2 | Tally ledger and stock item names mapped | Accountant | Back office → Tally → Mappings |
| 3 | GST slabs (5% / 18% at ₹2,500) | CA | Settings → `gst_slabs` |
| 4 | Other-state online orders: IGST is not calculated yet (all bills use CGST + SGST) | CA + developer | `app/core/gst.py` supports IGST; callers do not pass it yet |
| 5 | Shop GSTIN, name, bill footer | Owner | Settings |
| 6 | Discount limits per role, khata default limit and credit days | Owner | Settings |
| 7 | WhatsApp templates approved by the provider (Hindi + English) | Owner | Provider panel; `message_templates` |
| 8 | Razorpay live keys and webhook secret; one real ₹1 payment and refund | Owner | Razorpay dashboard |
| 9 | Shiprocket pickup location name matches | Online staff | Settings → `shiprocket_pickup_location` |
| 10 | Size charts, FAQ, complete-the-look in the shop's own words | Owner | Settings |
| 11 | AI monthly budget and cost rates vs the first Anthropic bill | Owner | Settings, AI tools → AI usage |
| 12 | Staff logins with the right roles and manager PINs | Owner | Settings → Staff |
| 13 | Opening khata balances entered (one `OPENING` entry per customer) | Accountant | Khata → account → adjustment |
| 14 | Opening stock counted | Manager | Stock → Stock count |
| 15 | Backups running and one restore tested | Developer | [backup-restore.md](backup-restore.md) |
| 16 | Manual tests that have no automated test (T02, T15–T17, T25, T27, T30, T31, T37–T40) | Team | [../testing.md](../testing.md) |

## Step 1 — Mode A + parallel run (about two weeks)

- Back office → Tally → Sync status: Mode **A**, POS **parallel** (the defaults).
- The counter keeps billing in TallyPrime as today. The Tally bridge reads each voucher and WearVerse updates
  shop stock, website stock and khata from it.
- Cashiers also enter bills in the WearVerse POS. These are **shadow bills**: saved for comparison only; they
  change no stock, khata or Tally.
- Every morning the accountant opens Tally → Reconciliation. Fix every difference (usually a missing item or
  ledger mapping) before the next day.
- The website can go live in this step: online orders reserve and deduct the same stock and post sales
  vouchers to Tally.

Exit rule: **14 days in a row with no reconciliation differences** and no open sync issues.

## Step 2 — Mode B (WearVerse POS is the counter)

1. At day close, make sure every POS device shows "all bills synced" and the register is closed.
2. Owner: Tally → Sync status → switch to **Mode B**. The cut-over date is recorded, the POS goes live and the
   new bill series (`C1-26-000001`) starts. Tally's own series is left as it is.
3. From now on POS bills deduct stock, post khata entries, send WhatsApp bills and push vouchers to Tally.
4. Keep the paper bill book at the counter for a full outage (no internet and no POS device). Enter those bills
   later with their original date and time (T40).

## Rollback

Switch back to **Mode A** in Tally → Sync status. Nothing is lost: vouchers that were not yet sent stay in the
outbox and go to Tally when the bridge next runs. The counter goes back to billing in Tally.

## First week in Mode B: watch

- Tally → Sync status: waiting vouchers near 0, heartbeat within the last minute.
- Dashboard alerts: negative stock (offline oversell), khata integrity, Tally backlog.
- Messages: failed WhatsApp sends, SMS fallbacks.
- Daily: cash register difference at day close.
