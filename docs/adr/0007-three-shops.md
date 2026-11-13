# ADR 0007: Three shops, each its own GST business

Status: accepted (Part 1 built). Extends ADR 0002: still one business owner and one software install, not a SaaS.

The business is **Sethi Saree Sansar**, with two more shops, **Sethi Suit** and **Sethi Kids**, in the same state.

Decisions from the owner:

| Topic | Decision |
|---|---|
| GST / Tally | Each shop has its own GSTIN and its own Tally company |
| Bills | Each shop issues its own bills (own series: `SSS-C1-…`, `SS-C1-…`, `SK-C1-…`) |
| Stock | Each shop has its own stock; pieces can move between shops |
| Khata | Separate per shop |
| Website | One site under the name Sethi Saree Sansar, selling from all three shops |

## Part 1 (built)

- `shops` table with code, name, GSTIN, state, address, phone, Tally company; one is the main shop (website,
  default for old data). Migration `743496565ef6` puts all existing data in Sethi Saree Sansar.
- Stock per shop: `stock_levels` and `stock_movements` carry `shop_id`; stock functions take a shop (default main).
- Counters belong to a shop; a POS device picks its counter once. Bills record their shop and print its name,
  GSTIN and address.
- Staff can be tied to one shop (they only see and bill for it) or work in all shops (owner, accountant).
  The back-office header picks the shop to show (`X-Shop-Id`); dashboard, bills, stock, sales and GST reports
  follow it.
- Purchases and purchase orders belong to the buying shop.
- Website: availability is all shops together; each order line holds stock in the shop that can send it
  (main shop first) and records that shop.
- Customer-facing name is `STORE_NAME` (API) / `VITE_STORE_NAME` (web), default "Sethi Saree Sansar".

## Part 2 (next)

Khata per shop; each shop's vouchers to its own Tally company (bridge handles several companies); messages and
Pay Now in the shop's name; employees and fall-pico per shop.

## Part 3 (after the CA)

Transfers between shops are sales between different GSTINs (tax invoice; sale in one Tally company, purchase in
the other). Website orders with items from two shops get one invoice per shop; whether payments go to one or
several Razorpay accounts is for the CA.
