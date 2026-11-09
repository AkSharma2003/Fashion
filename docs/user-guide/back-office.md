# Back-office guide

Open `/login` and sign in with your phone number and password; you land on your role's screen (owner/manager/accountant →
Dashboard, cashier → POS, online staff → Online orders, supervisor → Fall-pico, employee → My statement). The menu shows
only what your role may use.

| Menu | Who | What you do there |
|---|---|---|
| Dashboard | Owner, Manager, Accountant | Today's sales, khata due, online orders, alerts |
| POS billing | Cashier, Manager | Opens the POS ([pos-cashier.md](pos-cashier.md)) |
| Products | Manager, Cashier, Online staff | Add products, sizes/colours, prices, photos |
| Stock | Manager, Cashier, Online staff | Stock per item, history, adjustments, stock count |
| Bills | Manager, Cashier, Accountant | Find a bill, reprint, return |
| Online orders | Online staff, Manager | Pack, ship, deliver, returns |
| Khata | Manager, Cashier, Accountant | Accounts, ledger, payments, Pay Now links, messages |
| Fall-pico | Supervisor, Manager | Job board, workers, wages, cost |
| Purchasing | Manager, Accountant | Suppliers, supplier bills, purchase orders, labels |
| People | Manager, Accountant | Employees, attendance, advances |
| Salary | Accountant (Owner approves) | Monthly salary runs and payments |
| Tally | Accountant | Sync status, mode, issues, mappings, reconciliation |
| Reports | Accountant | Sales, GST, khata ageing |
| AI tools | Manager, Accountant, Online staff | What to buy, forecast, descriptions, posters, customer requests, AI usage |
| Settings | Owner / Admin | Shop rules, staff logins |
| My statement | Every staff member | Your own attendance, salary, advances |

Owner and Admin see everything.

## Products and stock

- **Products → New**: name, category (Sarees, Suits, Kids …), selling price, MRP, GST/HSN, "fall-pico eligible"
  for sarees. Then add variants (size, colour, price, cost) and photos. Each variant gets a SKU / barcode.
- **AI tools → Descriptions** can write a title, description and tags from the details and the photo. Read and
  edit before saving.
- **Stock**: the same stock is used by the shop and the website. Use **Adjust** with a reason for damage or
  found pieces; use **Stock count** after counting a shelf. Every change is kept in the history.

## Khata

- **Open account**: name, mobile, credit limit, credit days, opening balance, language, and tick "agreed to get
  bills on WhatsApp" only if the customer agreed.
- **Account page**: running ledger (newest first), balance, overdue amount.
  - **Receive payment** at the counter: amount and mode. It pays the oldest bills first; extra becomes advance.
  - **Send Pay Now link**: the customer gets a WhatsApp link to pay from home (valid 7 days).
  - **Adjustment / write-off / reversal**: owner only; a reversal keeps both entries visible.
  - **Dispute** tick stops automatic reminders while a bill is being checked.
  - **WhatsApp messages**: what was sent, delivery status, Resend.
- **Reports → Khata ageing**: who owes what, by age.

## Online orders

Order list by status. For each order:

1. `PAID` / `CONFIRMED` (COD) → if a saree needs fall-pico, the order waits until the job passes QC.
2. **Packed** → **Ship**: leave AWB empty to book Shiprocket automatically, or type the AWB from the courier.
3. **Delivered**. Returns: choose items and reason; online refunds go back through Razorpay.

**Messages from the website** (bottom of Online orders): what customers sent from the Contact page. Reply by
e-mail or phone, then **Mark done**.

## Fall-pico

Job board columns: Pending → Assigned → In progress → Completed → QC passed → Ready → Handed over. Assign a
worker, mark progress, do QC (pass or rework). The worker's wage is added once when QC passes. **Workers**: pay
wages, see each worker's statement. **Cost**: monthly wages and material.

## Purchasing

- **Suppliers**: name, phone, GSTIN, Tally ledger name.
- **New purchase** (goods arrived with the supplier bill): items, quantity, cost → stock goes up, labels to
  print, Tally purchase voucher.
- **Purchase orders**: draft → send → receive when goods arrive (creates the purchase). From **AI tools → What
  to buy** one click makes a draft purchase order.

## People and salary

- **People**: employees (monthly or daily pay, advance limit), daily attendance (P present, H half day, L paid
  leave, A absent, W weekly off), advances (above the limit needs the owner).
- **Salary**: create the month's run, check each line (days, incentive, overtime, advance recovery), the owner
  approves (then it is locked), record payments.
- **My statement**: each person sees only their own.

## Tally

- **Sync status**: mode A or B, POS parallel/live, last heartbeat, waiting vouchers. Switching mode is described
  in [../runbooks/going-live.md](../runbooks/going-live.md).
- **Sync issues**: what failed and why → fix the mapping → Retry, or Resolve with a note.
- **Mappings**: WearVerse customers, suppliers, items ↔ Tally ledger and stock item names.
- **Reconciliation**: daily WearVerse vs Tally totals; should show no differences.

## AI tools

| Tab | Use |
|---|---|
| What to buy | Items to reorder with quantity and budget, items customers asked for, rising categories, summary → Create purchase order |
| Forecast & trends | Expected sales for 7 / 30 / 90 days with confidence; what is selling faster |
| Descriptions | Write product text from details and photo |
| Poster maker | Square / story / banner poster with your text and product photos; download SVG or PNG |
| Customer requests | Things customers searched or asked for that we do not have; mark done |
| AI usage | Spend this month vs budget; rebuild search index |

AI suggestions are help, not decisions: check numbers before ordering.

## Settings (Owner)

Shop details, GST slabs, discount limits, khata defaults, reminders and quiet hours, website rules, AI switches
and budget, size charts, FAQ, and staff logins (role, password, manager PIN). Full list:
[../setup/configuration.md](../setup/configuration.md).
