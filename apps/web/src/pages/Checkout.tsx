import { STORE_NAME } from "../lib/brand";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Footer from "../components/Footer";
import Header from "../components/Header";
import { Alert, Field, Input } from "../components/ui";
import { apiData, errorMessage, post } from "../lib/api/client";
import { getCustomerToken } from "../lib/auth/session";
import { clearCart, getCart } from "../lib/cart";
import { formatINR } from "../lib/money";
import { useApi } from "../lib/hooks/useApi";
import { addressLines, customerApi, INDIAN_STATES, useCustomerProfile, type Address } from "../lib/customer";
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
  // Signed-in customers pick from their saved addresses (or add a new one, saved for next time).
  const { profile, signedIn } = useCustomerProfile();
  const saved = useApi(() => signedIn ? customerApi<Address[]>("/store/me/addresses") : Promise.resolve([] as Address[]), [signedIn]);
  const [choice, setChoice] = useState<string | null>(null);   // address id, "new", or null = not decided yet
  const [saveNew, setSaveNew] = useState(true);
  useEffect(() => {
    if (choice !== null || !saved.data) return;
    const pick = saved.data.find((a) => a.is_default) ?? saved.data[0];
    setChoice(pick ? pick.id : "new");
  }, [saved.data, choice]);
  useEffect(() => {
    const a = saved.data?.find((x) => x.id === choice);
    if (a) setAddr({ name: a.name, phone: a.phone, line1: a.line1, line2: a.line2 ?? "", landmark: a.landmark ?? "",
                     city: a.city, state: a.state, pincode: a.pincode });
    else if (choice === "new") setAddr({ name: profile?.full_name ?? "", phone: profile?.phone_number ?? "", line1: "", line2: "", landmark: "", city: "", state: "", pincode: "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [choice, saved.data]);
  useEffect(() => { if (profile?.email && !email) setEmail(profile.email); }, [profile, email]);
  const showForm = !signedIn || choice === "new";
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
      if (signedIn && choice === "new" && saveNew) {
        // Save to the address book; the order still goes ahead if this fails.
        await customerApi("/store/me/addresses", { method: "POST", body: JSON.stringify({
          ...addr, line2: addr.line2 || null, landmark: addr.landmark || null, kind: "HOME" }) }).catch(() => undefined);
      }
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
        name: STORE_NAME, description: `Order ${order.order_no}`, prefill: { name: addr.name, contact: addr.phone, email },
        onDone: () => { clearCart(); navigate(track); }, onDismiss: () => setBusy(false) });
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const set = (k: keyof typeof addr) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setAddr({ ...addr, [k]: e.target.value });

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-4 py-10 text-main_text">
        <form onSubmit={placeOrder} className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_360px]">
          <section className="space-y-4 rounded-2xl border border-divider bg-white p-6">
            <h1 className="sr-only">Checkout</h1>
            <h2 className="font-semibold">Delivery address</h2>
            {!signedIn && (
              <p className="text-sm text-text"><Link to="/login?next=/checkout" className="font-semibold text-primary underline">Sign in</Link> to use your saved addresses.</p>
            )}
            {signedIn && saved.loading && !saved.data && <p className="text-sm text-text">Loading your addresses…</p>}
            {signedIn && (saved.data?.length ?? 0) > 0 && (
              <div className="space-y-2" role="radiogroup" aria-label="Saved addresses">
                {saved.data!.map((a) => (
                  <label key={a.id} className={`flex cursor-pointer gap-3 rounded-xl border p-3 ${choice === a.id ? "border-primary bg-primary/5" : "border-divider"}`}>
                    <input type="radio" name="address" className="mt-1 accent-primary" checked={choice === a.id} onChange={() => setChoice(a.id)} />
                    <span className="text-sm">
                      <span className="font-semibold">{a.name}</span>
                      <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{a.kind === "HOME" ? "Home" : a.kind === "WORK" ? "Work" : "Other"}</span>
                      {a.is_default && <span className="ml-1 rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-800">Default</span>}
                      <span className="mt-1 block text-text">{addressLines(a)}</span>
                      <span className="block text-text">Phone: {a.phone}</span>
                    </span>
                  </label>
                ))}
                <label className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm font-medium ${choice === "new" ? "border-primary bg-primary/5" : "border-divider"}`}>
                  <input type="radio" name="address" className="accent-primary" checked={choice === "new"} onChange={() => setChoice("new")} />
                  + Deliver to a new address
                </label>
                <Link to="/account?tab=addresses" className="inline-block text-sm text-primary underline">Manage addresses</Link>
              </div>
            )}
            {showForm && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Full name"><Input required value={addr.name} onChange={set("name")} /></Field>
              <Field label="Mobile"><Input required inputMode="numeric" pattern="[0-9]{10}" maxLength={10} value={addr.phone} onChange={set("phone")} /></Field>
              <Field label="Address"><Input required value={addr.line1} onChange={set("line1")} /></Field>
              <Field label="Area / street (optional)"><Input value={addr.line2} onChange={set("line2")} /></Field>
              <Field label="Landmark (optional)"><Input value={addr.landmark} onChange={set("landmark")} /></Field>
              <Field label="City"><Input required value={addr.city} onChange={set("city")} /></Field>
              <Field label="State">
                <select required value={addr.state} onChange={set("state")}
                  className="min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
                  <option value="">Choose a state</option>
                  {INDIAN_STATES.map((st) => <option key={st}>{st}</option>)}
                </select>
              </Field>
              <Field label="PIN code"><Input required inputMode="numeric" pattern="[0-9]{6}" value={addr.pincode} onChange={set("pincode")} /></Field>
              {signedIn && (
                <label className="flex items-center gap-2 text-sm sm:col-span-2">
                  <input type="checkbox" className="accent-primary" checked={saveNew} onChange={(e) => setSaveNew(e.target.checked)} />
                  Save this address to my account
                </label>
              )}
            </div>
            )}
            <Field label="Email for the invoice (optional)"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
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
