import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Footer from "../components/Footer";
import Header from "../components/Header";
import { Alert, Badge, Field, Input } from "../components/ui";
import { apiData, errorMessage } from "../lib/api/client";
import { formatDate, formatINR } from "../lib/money";

type Order = { order_no: string; status: string; payment_method: string; total_paise: number; created_at: string;
  items: { id: string; product_name: string; qty: number; size: string | null; color: string | null }[];
  shipment: { courier: string; awb: string; tracking_url: string | null } | null };

const STEPS = ["PENDING_PAYMENT", "PAID", "FALL_PICO_IN_PROGRESS", "READY_TO_PACK", "PACKED", "SHIPPED", "DELIVERED"];
const LABEL: Record<string, string> = { PENDING_PAYMENT: "Waiting for payment", PAID: "Paid", CONFIRMED: "Confirmed (COD)",
  FALL_PICO_IN_PROGRESS: "Fall-pico being done", READY_TO_PACK: "Being packed", PACKED: "Packed", SHIPPED: "Shipped",
  DELIVERED: "Delivered", CANCELLED: "Cancelled", RETURNED: "Returned" };

export default function TrackOrder() {
  const [params] = useSearchParams();
  const [orderNo, setOrderNo] = useState(params.get("order") ?? "");
  const [phone, setPhone] = useState(params.get("phone") ?? "");
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");

  async function find(e?: React.FormEvent) {
    e?.preventDefault();
    try {
      setOrder(await apiData<Order>(`/store/orders/${encodeURIComponent(orderNo.trim())}?phone=${encodeURIComponent(phone.trim())}`));
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    if (params.get("order") && params.get("phone")) void find();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const step = order ? STEPS.indexOf(order.status === "CONFIRMED" ? "PAID" : order.status) : -1;

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-4 py-10 text-main_text">
        <div className="mx-auto max-w-2xl space-y-5">
          <h1 className="sr-only">Track your order</h1>
          <form onSubmit={find} className="grid gap-3 rounded-2xl border border-divider bg-white p-5 sm:grid-cols-[1fr_1fr_auto]">
            <Field label="Order number"><Input value={orderNo} onChange={(e) => setOrderNo(e.target.value)} placeholder="WV-000123" /></Field>
            <Field label="Mobile"><Input inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
            <button type="submit" className="min-h-11 self-end rounded-lg bg-primary px-5 font-semibold text-white">Track</button>
          </form>
          {error && <Alert>{error}</Alert>}
          {order && (
            <section className="space-y-4 rounded-2xl border border-divider bg-white p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-lg font-semibold">Order {order.order_no}</p>
                <Badge>{LABEL[order.status] ?? order.status}</Badge>
              </div>
              <p className="text-sm text-text">Placed {formatDate(order.created_at, true)} · {formatINR(order.total_paise)} · {order.payment_method === "COD" ? "Cash on delivery" : "Paid online"}</p>
              {step >= 0 && (
                <ol className="space-y-1 text-sm">
                  {STEPS.filter((s) => s !== "FALL_PICO_IN_PROGRESS" || order.status === s || step > 2).map((s) => (
                    <li key={s} className={STEPS.indexOf(s) <= step ? "font-semibold text-primary" : "text-gray-400"}>{STEPS.indexOf(s) <= step ? "✓" : "○"} {LABEL[s]}</li>
                  ))}
                </ol>
              )}
              <ul className="text-sm">{order.items.map((i) => <li key={i.id}>{i.qty} × {i.product_name} {[i.size, i.color].filter(Boolean).join(" / ")}</li>)}</ul>
              {order.shipment && <p className="text-sm">Courier {order.shipment.courier}, AWB {order.shipment.awb}{order.shipment.tracking_url && <> · <a className="underline" href={order.shipment.tracking_url} target="_blank" rel="noreferrer">track parcel</a></>}</p>}
            </section>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
