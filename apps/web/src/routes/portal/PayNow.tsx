import { useState } from "react";
import { useParams } from "react-router-dom";
import { Alert, Button, Input, Loading } from "../../components/ui";
import { apiData, errorMessage, post } from "../../lib/api/client";
import { useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";
import { openRazorpay } from "../../lib/payments/razorpay";
import { useT } from "../../lib/i18n";

type Portal = { shop_name: string; customer_first_name: string; balance_paise: number; test_mode: boolean; razorpay_key_id: string | null;
  entries: { type: string; amount_paise: number; label: string | null; running_balance_paise: number; date: string | null }[] };
type Start = { razorpay_order_id: string; amount_paise: number; key_id: string | null; test_mode: boolean; prefill: Record<string, string> };

/** Simple page for a khata customer: balance → choose amount → pay UPI → receipt (SRS 9.4 flow 3). */
export default function PayNow() {
  const { token = "" } = useParams();
  const { t } = useT();
  const portal = useApi(() => apiData<Portal>(`/pay/${encodeURIComponent(token)}`), [token]);
  const [amount, setAmount] = useState("");
  const [state, setState] = useState<"idle" | "paying" | "waiting" | "done">("idle");
  const [error, setError] = useState("");
  const p = portal.data;

  async function pay() {
    const paise = rupeesToPaise(amount || String((p?.balance_paise ?? 0) / 100));
    if (!paise || Number.isNaN(paise) || paise < 100) return setError("Enter an amount of at least ₹1.");
    setError("");
    setState("paying");
    try {
      const start = await post<Start>(`/pay/${encodeURIComponent(token)}/start`, { amount_paise: paise });
      if (start.test_mode || !start.key_id) {
        await post(`/pay/${encodeURIComponent(token)}/simulate/${start.razorpay_order_id}`);
        setState("done");
        void portal.reload();
        return;
      }
      await openRazorpay({ keyId: start.key_id, orderId: start.razorpay_order_id, amountPaise: start.amount_paise,
        name: p?.shop_name ?? "WearVerse", description: "Khata payment", prefill: start.prefill,
        onDone: () => { setState("waiting"); window.setTimeout(() => { void portal.reload(); setState("done"); }, 4000); },
        onDismiss: () => setState("idle") });
    } catch (err) {
      setError(errorMessage(err));
      setState("idle");
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-8 text-main_text">
      <div className="mx-auto max-w-md space-y-5">
        <div className="flex items-center justify-between"><h1 className="font-primaryFont text-3xl font-semibold text-primary">{p?.shop_name ?? "WearVerse"}</h1></div>
        {portal.loading && !p && <Loading />}
        {portal.error && <Alert>{portal.error}</Alert>}
        {p && (
          <>
            <section className="rounded-xl bg-white p-6 shadow-sm">
              <p className="text-lg">Namaste {p.customer_first_name} ji</p>
              <p className="mt-4 text-sm text-gray-600">{t("Your balance")}</p>
              <p className="text-4xl font-semibold tabular-nums">{p.balance_paise < 0 ? `${formatINR(-p.balance_paise)} advance` : formatINR(p.balance_paise)}</p>
            </section>
            {state === "done" ? (
              <Alert tone="good">Thank you! Your payment is received. A receipt is coming on WhatsApp.</Alert>
            ) : state === "waiting" ? (
              <Alert tone="warn">Confirming your payment with the bank…</Alert>
            ) : p.balance_paise > 0 && (
              <section className="space-y-3 rounded-xl bg-white p-6 shadow-sm">
                <label className="block text-lg">{t("Amount to pay (₹)")}
                  <Input inputMode="decimal" className="mt-2 !min-h-14 text-xl" placeholder={String(p.balance_paise / 100)} value={amount} onChange={(e) => setAmount(e.target.value)} />
                </label>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setAmount(String(p.balance_paise / 100))}>{t("Full amount")}</Button>
                </div>
                {error && <Alert>{error}</Alert>}
                <button type="button" disabled={state === "paying"} onClick={() => void pay()}
                  className="min-h-14 w-full rounded-lg bg-primary text-lg font-semibold text-white disabled:opacity-60">
                  {state === "paying" ? "…" : t("Pay with UPI / card")}</button>
                {p.test_mode && <p className="text-xs text-gray-500">Test mode: payment is simulated (no real money).</p>}
              </section>
            )}
            <section className="rounded-xl bg-white p-6 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold">{t("Recent bills and payments")}</h2>
              <ul className="divide-y divide-gray-100 text-base">
                {p.entries.map((e, i) => (
                  <li key={i} className="flex justify-between py-2">
                    <span>{e.type === "SALE" ? `Bill ${e.label ?? ""}` : e.type === "PAYMENT" ? "Payment" : e.type.toLowerCase()}<br /><span className="text-sm text-gray-500">{formatDate(e.date)}</span></span>
                    <span className={e.amount_paise < 0 ? "text-[#1E8E3E]" : ""}>{e.amount_paise < 0 ? "−" : ""}{formatINR(Math.abs(e.amount_paise))}</span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
