# Website guide (for customers and online staff)

What a customer can do on the website, so staff can help them on the phone.

## Shopping

- Browse **Sarees**, **Suits**, **Kids**, **New arrivals**, or search. Search understands simple Hindi / Hinglish:
  "lal silk saree under 5000", "kids lehenga". On the search page, **Search by photo** finds items with a similar colour and pattern.
- Product page: sizes and colours with live stock (the same stock as the shop), **Size help** (size chart and
  "fits small / big" from past returns), similar items, "complete the look", "customers also bought".
- Sarees above ₹1,000 come with free fall-pico; the customer can skip it at checkout.
- The chat button answers common questions (delivery, returns, COD) and order status. It tells the customer it
  is an AI assistant, never gives discounts or khata balances, and shows an order only to its owner (logged in,
  or with the order's mobile number).
- Sign in at `/login` with mobile or e-mail and password, or **Continue with Google** (new Google users add their mobile number once).

## Checkout

1. Cart → **Checkout**: name, mobile, address with 6-digit pincode, e-mail (optional).
2. Pay **online** (UPI / card / net banking through Razorpay) or **cash on delivery**. Khata is not available
   online.
3. The items are held for 30 minutes while the customer pays. If payment fails they can retry from the order page;
   after 30 minutes unpaid, the items are released.
4. On payment the customer gets an order number (`WV-000123`) and a WhatsApp confirmation.

## After the order

- **Track order** (`/track`): order number + mobile number shows status and courier tracking.
- **Account** (`/account`, login with mobile or e-mail and password; new customers register with an OTP): my orders.
- Returns (shop policy: 7 days): the customer contacts the shop; online staff create the return in Online
  orders for a shipped or delivered order, and the refund goes back to the original payment method.

## Pay khata from home

Khata customers get a WhatsApp message with a **Pay Now** link (`/pay/<code>`, valid 7 days). It shows the
balance and recent bills; the customer can pay all or part by UPI or card. The receipt comes on WhatsApp. A link
that has expired shows a message to ask the shop for a new one.
