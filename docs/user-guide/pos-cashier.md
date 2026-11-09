# POS guide for cashiers

The POS is at `/pos` on the counter PC (or a tablet). Log in once with your phone and password; after that it
keeps working even without internet. Cashiers open straight on the POS after signing in at `/login`.

## Start of day

1. Open `/pos`. The top bar shows whether you are online.
2. **Cash register → Opening cash ₹**: type the cash in the drawer and open the register.

## Make a bill

1. Press **F2** (or click the box) and scan the barcode, or type the item name.
2. Change quantity if needed. To give a discount, type it in **Discount ₹** on the line.
   - Cashiers can give up to 5% without approval. Above that, the **Manager PIN** box appears; the manager types
     their PIN and a reason.
3. **Khata customer (optional)**: search by name or mobile number if the customer is buying on khata or wants the
   bill on WhatsApp.
4. Press **F4 / Take payment** and choose how they pay. You can split one bill:
   - **CASH** (type "Cash given by customer" to see the change)
   - **UPI**, **CARD** (type the reference if there is one)
   - **KHATA** (udhar) — only for a chosen khata customer. If it goes over their credit limit, a manager PIN is
     needed.
5. Save. The bill prints and, for a khata customer, a WhatsApp bill is sent.

Sarees above ₹1,000 show a fall-pico tick on the line, already ticked; a free fall-pico job is made when the bill
is saved. If the customer does not want fall-pico, untick it before saving.

**Hold bill** keeps a half-made bill aside so you can serve the next customer; open it again from the held list.

## When the internet goes

Keep billing. The bill is saved on the device, printed, and shown under **Bills waiting to sync**. When the
internet returns, they go to the server by themselves. Khata on offline bills is allowed up to 80% of the
customer's limit.

If a waiting bill shows a red reason (for example the price changed, or approval needed), call the manager —
fixing and resending it never makes a second bill.

If the POS device itself does not work, write the bill in the paper bill book and give the book to the manager;
the bills are entered later with the original date and time.

## Returns

**Returns** → type or scan the bill number → choose items and quantity → refund mode (cash, UPI, khata,
exchange). A return needs the manager (or their PIN); after 7 days it needs the owner. A khata bill return
reduces the customer's balance.

## End of day

1. Check **To sync** is 0 (all bills synced). The register cannot close while bills are waiting.
2. **Cash register → Counted cash ₹**: count the drawer and close. The difference is saved for the manager.
