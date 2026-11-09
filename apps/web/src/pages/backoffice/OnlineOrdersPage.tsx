import { useState } from "react";
import BarcodeScanner from "../../components/backoffice/BarcodeScanner";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Select, Table } from "../../components/ui";
import { apiData, patch, post } from "../../lib/api/client";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate } from "../../lib/money";

type OrderItem = { id: string; product_name: string; sku: string; size: string | null; color: string | null; qty: number;
  line_total_paise: number; fall_pico_skipped: boolean; returned_qty: number };
type Order = { id: string; order_no: string; status: string; payment_method: string; ship_name: string; ship_phone: string;
  ship_address: Record<string, string | null>; total_paise: number; created_at: string; items: OrderItem[];
  fall_pico_jobs: { id: string; tag_code: string; status: string }[];
  shipment: { courier: string; awb: string; tracking_url: string | null } | null };

const TABS: { label: string; status: string }[] = [
  { label: "To pack", status: "READY_TO_PACK" },
  { label: "Waiting for fall-pico", status: "FALL_PICO_IN_PROGRESS" },
  { label: "Packed", status: "PACKED" },
  { label: "Shipped", status: "SHIPPED,DELIVERED" },
  { label: "Unpaid", status: "PENDING_PAYMENT" },
  { label: "Closed", status: "CANCELLED,RETURNED" },
];

export default function OnlineOrdersPage() {
  const [tab, setTab] = useState(TABS[0].status);
  const orders = useApi(() => apiData<Order[]>(`/orders?status=${tab}`), [tab]);
  const [sel, setSel] = useState<Order | null>(null);

  return (
    <Page title="Online orders" crumb="Website">
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <Button key={t.status} variant={t.status === tab ? "primary" : "secondary"} onClick={() => setTab(t.status)}>{t.label}</Button>
        ))}
      </div>
      <Card>
        {orders.loading && !orders.data && <Loading />}
        <Alert>{orders.error}</Alert>
        <Table rows={orders.data ?? []} rowKey={(o) => o.id} onRowClick={setSel} empty="No orders here." columns={[
          { key: "no", label: "Order", render: (o) => <div><p className="font-medium">{o.order_no}</p><p className="text-xs text-gray-500">{formatDate(o.created_at, true)}</p></div> },
          { key: "c", label: "Customer", render: (o) => <div>{o.ship_name}<p className="text-xs text-gray-500">{o.ship_address.city}</p></div> },
          { key: "i", label: "Items", render: (o) => o.items.map((i) => `${i.qty}× ${i.product_name}`).join(", ") },
          { key: "s", label: "Status", render: (o) => <div className="flex flex-wrap gap-1"><Badge>{o.status}</Badge>{o.payment_method === "COD" && <Badge tone="info">COD</Badge>}</div> },
          { key: "t", label: "Total", align: "right", render: (o) => <Money paise={o.total_paise} /> },
        ]} />
      </Card>
      {sel && <OrderModal order={sel} onClose={() => { setSel(null); void orders.reload(); }} />}
      <ContactMessages />
    </Page>
  );
}

function OrderModal({ order: initial, onClose }: { order: Order; onClose: () => void }) {
  const [order, setOrder] = useState(initial);
  const act = useAction();
  const [picked, setPicked] = useState<Record<string, number>>({});
  const [awb, setAwb] = useState("");
  const [courier, setCourier] = useState("Shiprocket");
  const [returnQty, setReturnQty] = useState<Record<string, string>>({});
  const allPicked = order.items.every((i) => (picked[i.sku] ?? 0) >= i.qty);

  async function setStatus(status: string, note?: string) {
    const r = await act.run(() => patch<Order>(`/orders/${order.id}/status`, { status, note }), `Order is now ${status.replace(/_/g, " ").toLowerCase()}.`);
    if (r) setOrder(r);
  }

  function onScan(code: string) {
    const item = order.items.find((i) => i.sku === code.trim());
    if (!item) return act.setError(`Scanned ${code} is not in this order.`);
    act.setError("");
    setPicked((p) => ({ ...p, [item.sku]: Math.min((p[item.sku] ?? 0) + 1, item.qty) }));
  }

  const a = order.ship_address;
  return (
    <Modal open title={`Order ${order.order_no}`} onClose={onClose} wide>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2"><Badge>{order.status}</Badge><Badge tone="info">{order.payment_method}</Badge></div>
        <p className="text-sm">{order.ship_name} · {order.ship_phone}<br />
          <span className="text-gray-600">{[a.line1, a.line2, a.landmark, a.city, a.state, a.pincode].filter(Boolean).join(", ")}</span></p>
        <Alert tone="good">{act.notice}</Alert><Alert>{act.error}</Alert>

        <Card title="Pick list">
          <ul className="space-y-2 text-sm">
            {order.items.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3">
                <span>{i.qty}× {i.product_name} <span className="text-xs text-gray-500">{i.sku} {[i.size, i.color].filter(Boolean).join(" / ")}</span></span>
                <Badge tone={(picked[i.sku] ?? 0) >= i.qty ? "good" : "warn"}>{`${picked[i.sku] ?? 0}/${i.qty} scanned`}</Badge>
              </li>
            ))}
          </ul>
          {order.status === "READY_TO_PACK" && <div className="mt-4"><BarcodeScanner onScan={onScan} /></div>}
        </Card>

        {order.fall_pico_jobs.length > 0 && (
          <Card title="Fall-pico">
            <div className="flex flex-wrap gap-2">{order.fall_pico_jobs.map((j) => <span key={j.id} className="text-sm">{j.tag_code} <Badge>{j.status}</Badge></span>)}</div>
            <p className="mt-2 text-xs text-gray-500">The order can be packed only after QC passes (or the customer skipped fall-pico).</p>
          </Card>
        )}

        <div className="flex flex-wrap gap-2">
          {order.status === "READY_TO_PACK" && <Button disabled={act.busy || !allPicked} onClick={() => void setStatus("PACKED")}>Mark packed</Button>}
          {order.status === "SHIPPED" && <Button onClick={() => void setStatus("DELIVERED")}>Mark delivered</Button>}
          {["PAID", "CONFIRMED", "READY_TO_PACK", "FALL_PICO_IN_PROGRESS", "PACKED", "PENDING_PAYMENT"].includes(order.status) && (
            <Button variant="danger" disabled={act.busy} onClick={() => { if (window.confirm("Cancel this order? Paid orders are refunded.")) void setStatus("CANCELLED", "Cancelled by staff"); }}>Cancel order</Button>
          )}
        </div>

        {order.status === "PACKED" && (
          <Card title="Create shipment">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Courier"><Input value={courier} onChange={(e) => setCourier(e.target.value)} /></Field>
              <Field label="AWB number" hint="Leave empty to book on Shiprocket"><Input value={awb} onChange={(e) => setAwb(e.target.value)} /></Field>
              <div className="flex items-end"><Button disabled={act.busy} onClick={async () => {
                const r = await act.run(() => post<{ awb: string; courier: string; tracking_url: string | null }>(`/orders/${order.id}/shipment`, { courier, awb: awb || null }), "Shipment created.");
                if (r) setOrder({ ...order, status: "SHIPPED", shipment: r });
              }}>Ship</Button></div>
            </div>
          </Card>
        )}
        {order.shipment && <p className="text-sm">Shipped with {order.shipment.courier}, AWB {order.shipment.awb}</p>}

        {["SHIPPED", "DELIVERED"].includes(order.status) && (
          <Card title="Return items (manager)">
            {order.items.map((i) => (
              <div key={i.id} className="mb-2 flex items-center gap-3 text-sm">
                <span className="flex-1">{i.product_name} (bought {i.qty}, returned {i.returned_qty})</span>
                <Select className="w-24" value={returnQty[i.id] ?? "0"} onChange={(e) => setReturnQty({ ...returnQty, [i.id]: e.target.value })}>
                  {Array.from({ length: i.qty - i.returned_qty + 1 }, (_, n) => <option key={n}>{n}</option>)}
                </Select>
              </div>
            ))}
            <Button variant="secondary" disabled={act.busy} onClick={async () => {
              const items = Object.entries(returnQty).filter(([, q]) => Number(q) > 0).map(([order_item_id, q]) => ({ order_item_id, qty: Number(q) }));
              if (!items.length) return;
              await act.run(() => post(`/orders/${order.id}/returns`, { items }), "Return saved; stock is back and refund started.");
            }}>Save return</Button>
          </Card>
        )}
      </div>
    </Modal>
  );
}

type ContactMessage = { id: string; name: string; email: string; phone: string | null; message: string; status: string; created_at: string };

/** Messages customers sent from the website's Contact page. */
function ContactMessages() {
  const [showDone, setShowDone] = useState(false);
  const msgs = useApi(() => apiData<ContactMessage[]>(`/store/contact-messages?status=${showDone ? "DONE" : "NEW"}`), [showDone]);
  const act = useAction();
  return (
    <Card title="Messages from the website" actions={
      <Button variant="secondary" onClick={() => setShowDone(!showDone)}>{showDone ? "Show new" : "Show done"}</Button>}>
      {msgs.loading && !msgs.data && <Loading />}
      <Alert>{msgs.error || act.error}</Alert>
      <Table rows={msgs.data ?? []} rowKey={(m) => m.id} empty={showDone ? "No answered messages." : "No new messages."} columns={[
        { key: "from", label: "From", render: (m) => <div><p className="font-medium">{m.name}</p>
          <p className="text-xs text-gray-500"><a className="underline" href={`mailto:${m.email}`}>{m.email}</a>{m.phone ? ` · ${m.phone}` : ""}</p></div> },
        { key: "message", label: "Message", render: (m) => <p className="max-w-xl whitespace-pre-wrap text-sm">{m.message}</p> },
        { key: "when", label: "Received", render: (m) => formatDate(m.created_at, true) },
        { key: "act", label: "", render: (m) => (
          <Button variant="secondary" disabled={act.busy} onClick={async () => {
            await act.run(() => patch(`/store/contact-messages/${m.id}`, { status: m.status === "NEW" ? "DONE" : "NEW" }));
            void msgs.reload();
          }}>{m.status === "NEW" ? "Mark done" : "Mark new"}</Button>) },
      ]} />
    </Card>
  );
}
