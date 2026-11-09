# Daily operations

What the shop team does each day, and what runs by itself.

## Runs by itself (worker schedule, Asia/Kolkata)

| Job | Every | What it does |
|---|---|---|
| Send messages | 10 s | Sends waiting WhatsApp / SMS jobs (respects quiet hours 21:00–09:00 for reminders) |
| Release expired orders | 1 min | Unpaid website orders older than 30 min give their stock back |
| Tally backlog check | 5 min | Alert when vouchers wait longer than 30 min or the bridge is silent |
| Khata reminders | 1 hour | Reminders 7, 15, 30 days after a bill, weekly once overdue; skips disputed / paused / opted-out |
| Khata integrity | 1 day | Recomputes every balance from the ledger; any difference is an alert |
| Tally reconciliation | 1 day | Compares the day's totals with Tally |
| AI refresh | 1 day | Rebuilds the search index and forecasts; deletes chat history older than 90 days |

If the worker is down, nothing is lost: work waits in the outbox and runs when it starts again.

## Opening (cashier / manager)

1. Open `/pos` on the counter PC. Check the top bar says online (or "offline — bills saved").
2. Open the register with the opening cash.
3. Dashboard: look at alerts from the night (negative stock, Tally backlog, integrity).

## During the day

| Task | Where |
|---|---|
| Billing, holds, returns, split payments | POS |
| Customer pays khata at the counter | Khata → account → Receive payment |
| Send a Pay Now link | Khata → account → Send Pay Now link |
| Online orders: pack, ship (AWB auto or typed), returns | Online orders |
| Fall-pico jobs: assign, complete, QC, hand over | Fall-pico |
| New stock from a supplier | Purchasing → New purchase, or receive a purchase order; print labels |
| Attendance | People → Attendance |
| Customer requests (things people asked for) | AI tools → Customer requests |

## Closing (cashier / manager)

1. Make sure the POS shows **all bills synced**. A register cannot close while offline bills are waiting
   (`BILLS_NOT_SYNCED`).
2. Count the cash and close the register. The difference (expected − counted) is saved with the day summary.
3. Hand over the bill book if it was used during an outage; enter those bills next morning with the original
   date and time.

## Accountant, each morning

1. Tally → Sync status: heartbeat recent, waiting vouchers near 0.
2. Tally → Sync issues: map the unknown party or item, then **Retry**; or **Resolve** with a note.
3. Tally → Reconciliation: yesterday should show no differences.
4. Reports → Khata ageing: overdue customers; disputes.

## Monthly

| Task | Who | Where |
|---|---|---|
| Salary run: create, check lines, owner approves, record payments | Accountant, Owner | Salary |
| Fall-pico worker payments and monthly cost | Supervisor, Accountant | Fall-pico → Workers, Cost |
| GST report for the CA | Accountant | Reports → GST |
| What to buy, forecast, trends → purchase orders | Owner, Manager | AI tools |
| AI spend vs budget | Owner | AI tools → AI usage |
| Stock count of a few categories | Manager | Stock → Stock count |
