import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Footer from "../components/Footer";
import Header from "../components/Header";
import { Alert, Field, Input } from "../components/ui";
import { apiData, errorMessage, post } from "../lib/api/client";
import { getCustomerToken } from "../lib/auth/session";
import { clearCart, getCart } from "../lib/cart";
import { formatINR } from "../lib/money";
import { openRazorpay } from "../lib/payments/razorpay";

type CheckoutResult = {
  order: { order_no: string; total_paise: number; status: string; ship_phone: string };
  payment: { razorpay_order_id: string; key_id: string | null; amount_paise: number; test_mode: boolean } | null;
};

function newKey() {
  return `cart-${crypto.randomUUID()}`;
}

/** Website checkout (FR-CHK). Online customers pay online or cash on delivery; never khata (T28). */
export default function Checkout() {
  const navigate = useNavigate();
  const items = useMemo(() => getCart(), []);
  const missingSize = items.filter((i) => !i.variantId);
  const [addr, setAddr] = useState({ name: "", phone: "", line1: "", line2: "", landmark: "", city: "", state: "", pincode: "" });
  const [email, setEmail] = useState("");
  const [method, setMethod] = useState<"ONLINE" | "COD">("ONLINE");
  const [skip, setSkip] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // Same key for this checkout so a double click on Pay makes one order (T26).
  const [key] = useState(newKey);
  const total = items.reduce((s, i) => s + Math.round(i.product.price * 100) * i.quantity, 0);

  async function placeOrder(e: React.FormEvent) {
    e.preventDefault();
    if (missingSize.length) return setError("Choose a size/colour for every item first.");
    setBusy(true);
    setError("");
    try {
      const customerToken = getCustomerToken();
      const result = await apiData<CheckoutResult>("/store/checkout", {
        method: "POST",
        headers: customerToken ? { Authorization: `Bearer ${customerToken}` } : undefined,
        body: JSON.stringify({
          idempotency_key: key, payment_method: method, email: email || null,
          address: { ...addr, line2: addr.line2 || null, landmark: addr.landmark || null },
          items: items.map((i) => ({ variant_id: i.variantId, qty: i.quantity, fall_pico_skip: Boolean(skip[i.variantId ?? ""]) })),
        }),
      });
      const { order, payment } = result;
      const track = `/track?order=${encodeURIComponent(order.order_no)}&phone=${encodeURIComponent(order.ship_phone)}`;
      if (!payment) { clearCart(); navigate(track); return; }
      if (payment.test_mode || !payment.key_id) {
        await post(`/store/orders/${order.order_no}/simulate-payment?phone=${encodeURIComponent(order.ship_phone)}`);
        clearCart(); navigate(track); return;
      }
      await openRazorpay({ keyId: payment.key_id, orderId: payment.razorpay_order_id, amountPaise: payment.amount_paise,
        name: "WearVerse", description: `Order ${order.order_no}`, prefill: { name: addr.name, contact: addr.phone, email },
        onDone: () => { clearCart(); navigate(track); }, onDismiss: () => setBusy(false) });
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const set = (k: keyof typeof addr) => (e: React.ChangeEvent<HTMLInputElement>) => setAddr({ ...addr, [k]: e.target.value });

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-4 py-10 text-main_text">
        <form onSubmit={placeOrder} className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_360px]">
          <section className="space-y-4 rounded-2xl border border-divider bg-white p-6">
            <h1 className="font-primaryFont text-3xl font-semibold">Checkout</h1>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Full name"><Input required value={addr.name} onChange={set("name")} /></Field>
              <Field label="Mobile"><Input required inputMode="tel" pattern="[0-9]{10,15}" value={addr.phone} onChange={set("phone")} /></Field>
              <Field label="Address"><Input required value={addr.line1} onChange={set("line1")} /></Field>
              <Field label="Area / street (optional)"><Input value={addr.line2} onChange={set("line2")} /></Field>
              <Field label="Landmark (optional)"><Input value={addr.landmark} onChange={set("landmark")} /></Field>
              <Field label="City"><Input required value={addr.city} onChange={set("city")} /></Field>
              <Field label="State"><Input required value={addr.state} onChange={set("state")} /></Field>
              <Field label="PIN code"><Input required inputMode="numeric" pattern="[0-9]{6}" value={addr.pincode} onChange={set("pincode")} /></Field>
              <Field label="Email for the invoice (optional)"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            </div>
            <fieldset className="space-y-2">
              <legend className="font-semibold">Payment</legend>
              <label className="flex items-center gap-2"><input type="radio" checked={method === "ONLINE"} onChange={() => setMethod("ONLINE")} /> UPI / card / net banking</label>
              <label className="flex items-center gap-2"><input type="radio" checked={method === "COD"} onChange={() => setMethod("COD")} /> Cash on delivery</label>
            </fieldset>
          </section>
          <aside className="h-fit space-y-3 rounded-2xl border border-divider bg-white p-6">
            <h2 className="font-semibold">Your order</h2>
            {items.length === 0 && <p className="text-sm">Your cart is empty. <Link to="/" className="underline">Shop now</Link></p>}
            <ul className="space-y-3 text-sm">
              {items.map((i) => (
                <li key={`${i.product.name}-${i.variantId}`}>
                  <div className="flex justify-between gap-2"><span>{i.quantity} × {i.product.name} {[i.size, i.color].filter(Boolean).join(" / ")}</span>
                    <span>{formatINR(Math.round(i.product.price * 100) * i.quantity)}</span></div>
                  {!i.variantId && <p className="text-sale">Choose a size on the product page.</p>}
                  {i.variantId && /saree/i.test(i.product.name) && (
                    <label className="mt-1 flex items-center gap-2 text-xs text-text">
                      <input type="checkbox" checked={Boolean(skip[i.variantId])} onChange={(e) => setSkip({ ...skip, [i.variantId!]: e.target.checked })} />
                      Skip free fall-pico (ships sooner)</label>
                  )}
                </li>
              ))}
            </ul>
            <div className="flex justify-between border-t border-divider pt-3 font-semibold"><span>Total</span><span>{formatINR(total)}</span></div>
            <p className="text-xs text-text">Final price, GST and stock are checked again when you place the order.</p>
            {error && <Alert>{error}</Alert>}
            <button type="submit" disabled={busy || !items.length}
              className="min-h-12 w-full rounded-lg bg-primary font-semibold text-white disabled:opacity-60">
              {busy ? "Please wait…" : method === "COD" ? "Place order" : "Pay and place order"}</button>
          </aside>
        </form>
      </main>
      <Footer />
    </>
  );
}
