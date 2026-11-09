import { useMemo, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Modal, Money, Page, Select, Table } from "../../components/ui";
import { api, apiData, post } from "../../lib/api/client";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";

type Supplier = { id: string; name: string; phone: string | null; gstin: string | null; city: string | null };
type Purchase = { id: string; purchase_no: string; supplier: string; supplier_bill_no: string; bill_date: string; total_paise: number; source: string };
type StockRow = { variant_id: string; product_name: string; sku: string; size: string | null; color: string | null };
type Line = { variant_id: string; qty: string; cost: string; gst: string };
type Label = { barcode: string; name: string; size: string | null; color: string | null; price_paise: number; mrp_paise: number | null };

export default function PurchasingPage() {
  const suppliers = useApi(() => apiData<Supplier[]>("/purchases/suppliers"));
  const purchases = useApi(() => apiData<Purchase[]>("/purchases"));
  const variants = useApi(() => api<StockRow[]>("/inventory/stock"));
  const act = useAction();
  const [sup, setSup] = useState({ name: "", phone: "", gstin: "", city: "" });
  const [bill, setBill] = useState({ supplier_id: "", supplier_bill_no: "", bill_date: new Date().toISOString().slice(0, 10) });
  const [lines, setLines] = useState<Line[]>([{ variant_id: "", qty: "1", cost: "", gst: "5" }]);
  const [labels, setLabels] = useState<Label[] | null>(null);
  const total = useMemo(() => lines.reduce((s, l) => {
    const t = (rupeesToPaise(l.cost) || 0) * (Number(l.qty) || 0);
    return s + t + Math.round((t * (Number(l.gst) || 0)) / 100);
  }, 0), [lines]);

  async function save() {
    const items = lines.filter((l) => l.variant_id).map((l) => ({ variant_id: l.variant_id, qty: Number(l.qty),
      unit_cost_paise: rupeesToPaise(l.cost), gst_rate_bp: Math.round(Number(l.gst) * 100) }));
    const r = await act.run(() => post<{ id: string; purchase_no: string }>("/purchases", { ...bill, items }), "Purchase saved. Stock added and Tally purchase voucher queued.");
    if (r) {
      setLines([{ variant_id: "", qty: "1", cost: "", gst: "5" }]);
      setLabels(await apiData<Label[]>(`/purchases/${r.id}/labels`));
      void purchases.reload();
    }
  }

  return (
    <Page title="Purchasing" crumb="Stock in">
      <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      <Card title="New supplier bill">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Supplier"><Select value={bill.supplier_id} onChange={(e) => setBill({ ...bill, supplier_id: e.target.value })}>
            <option value="">Choose…</option>{(suppliers.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></Field>
          <Field label="Supplier bill no."><Input value={bill.supplier_bill_no} onChange={(e) => setBill({ ...bill, supplier_bill_no: e.target.value })} /></Field>
          <Field label="Bill date"><Input type="date" value={bill.bill_date} onChange={(e) => setBill({ ...bill, bill_date: e.target.value })} /></Field>
        </div>
        <div className="mt-4 space-y-2">
          {lines.map((l, i) => (
            <div key={i} className="grid gap-2 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
              <Select value={l.variant_id} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, variant_id: e.target.value } : x))}>
                <option value="">Item…</option>
                {(variants.data ?? []).map((v) => <option key={v.variant_id} value={v.variant_id}>{v.product_name} · {v.sku} {[v.size, v.color].filter(Boolean).join("/")}</option>)}
              </Select>
              <Input placeholder="Qty" inputMode="numeric" value={l.qty} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, qty: e.target.value } : x))} />
              <Input placeholder="Cost ₹ (before GST)" inputMode="decimal" value={l.cost} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, cost: e.target.value } : x))} />
              <Input placeholder="GST %" inputMode="decimal" value={l.gst} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, gst: e.target.value } : x))} />
              <Button variant="ghost" onClick={() => setLines(lines.filter((_, j) => j !== i))}>✕</Button>
            </div>
          ))}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button variant="secondary" onClick={() => setLines([...lines, { variant_id: "", qty: "1", cost: "", gst: "5" }])}>Add line</Button>
            <p className="text-sm">Bill total: <b>{formatINR(total)}</b></p>
          </div>
          <Button disabled={act.busy || !bill.supplier_id || !bill.supplier_bill_no} onClick={() => void save()}>Save and add stock</Button>
        </div>
      </Card>

      {labels && (
        <Card title={`Labels to print (${labels.length})`} actions={<Button variant="secondary" onClick={() => window.print()}>Print</Button>}>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 print:grid-cols-4">
            {labels.map((l, i) => (
              <div key={i} className="rounded border border-gray-300 p-2 text-center text-xs">
                <p className="font-semibold">{l.name}</p><p>{[l.size, l.color].filter(Boolean).join(" / ")}</p>
                <p className="my-1 font-mono text-sm tracking-widest">{l.barcode}</p>
                <p className="font-semibold">{formatINR(l.price_paise)}{l.mrp_paise ? ` (MRP ${formatINR(l.mrp_paise)})` : ""}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Purchases">
          <Table rows={purchases.data ?? []} rowKey={(p) => p.id} empty="No purchases yet." columns={[
            { key: "n", label: "No.", render: (p) => <div><p className="font-medium">{p.purchase_no}</p><p className="text-xs text-gray-500">{p.supplier} · {p.supplier_bill_no}</p></div> },
            { key: "d", label: "Date", render: (p) => formatDate(p.bill_date) },
            { key: "t", label: "Total", align: "right", render: (p) => <Money paise={p.total_paise} /> },
            { key: "l", label: "", render: (p) => <button type="button" className="text-xs underline" onClick={async () => setLabels(await apiData<Label[]>(`/purchases/${p.id}/labels`))}>Labels</button> },
          ]} />
        </Card>
        <Card title="Add supplier">
          <div className="grid gap-2 sm:grid-cols-2">
            <Input placeholder="Name" value={sup.name} onChange={(e) => setSup({ ...sup, name: e.target.value })} />
            <Input placeholder="Phone" value={sup.phone} onChange={(e) => setSup({ ...sup, phone: e.target.value })} />
            <Input placeholder="GSTIN" value={sup.gstin} onChange={(e) => setSup({ ...sup, gstin: e.target.value })} />
            <Input placeholder="City" value={sup.city} onChange={(e) => setSup({ ...sup, city: e.target.value })} />
          </div>
          <Button className="mt-3" disabled={act.busy || sup.name.length < 2} onClick={async () => {
            await act.run(() => post("/purchases/suppliers", { name: sup.name, phone: sup.phone || null, gstin: sup.gstin || null, city: sup.city || null }), "Supplier added.");
            setSup({ name: "", phone: "", gstin: "", city: "" }); void suppliers.reload(); }}>Add supplier</Button>
        </Card>
      </div>
      <PurchaseOrders suppliers={suppliers.data ?? []} variants={variants.data ?? []} onReceived={() => void purchases.reload()} />
    </Page>
  );
}


type PO = { id: string; po_no: string; status: string; supplier: string; expected_on: string | null; total_paise: number; created_at: string;
  items: { id: string; variant_id: string | null; description: string; qty: number; unit_cost_paise: number; received_qty: number }[] };

/** Phase 2 purchase orders: draft (by hand or from What-to-buy), send, receive into stock. */
function PurchaseOrders({ suppliers, variants, onReceived }: { suppliers: Supplier[]; variants: StockRow[]; onReceived: () => void }) {
  const pos = useApi(() => apiData<PO[]>("/purchases/orders"));
  const act = useAction();
  const [draft, setDraft] = useState({ supplier_id: "", variant_id: "", description: "", qty: "1", cost: "" });
  const [lines, setLines] = useState<{ variant_id: string | null; description: string; qty: number; unit_cost_paise: number }[]>([]);
  const [receiving, setReceiving] = useState<PO | null>(null);
  const [bill, setBill] = useState({ no: "", date: new Date().toISOString().slice(0, 10) });
  const [qty, setQty] = useState<Record<string, string>>({});

  return (
    <Card title="Purchase orders">
      <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_1.5fr_1fr_0.6fr_0.8fr_auto]">
        <Select value={draft.supplier_id} onChange={(e) => setDraft({ ...draft, supplier_id: e.target.value })}>
          <option value="">Supplier…</option>{suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select>
        <Select value={draft.variant_id} onChange={(e) => setDraft({ ...draft, variant_id: e.target.value })}>
          <option value="">New item (type below)…</option>{variants.map((v) => <option key={v.variant_id} value={v.variant_id}>{v.product_name} · {v.sku}</option>)}</Select>
        <Input placeholder="Description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
        <Input placeholder="Qty" inputMode="numeric" value={draft.qty} onChange={(e) => setDraft({ ...draft, qty: e.target.value })} />
        <Input placeholder="Cost ₹" inputMode="decimal" value={draft.cost} onChange={(e) => setDraft({ ...draft, cost: e.target.value })} />
        <Button variant="secondary" disabled={!Number(draft.qty) || (!draft.variant_id && !draft.description)} onClick={() => {
          setLines([...lines, { variant_id: draft.variant_id || null, description: draft.description, qty: Number(draft.qty), unit_cost_paise: rupeesToPaise(draft.cost || "0") || 0 }]);
          setDraft({ ...draft, variant_id: "", description: "", qty: "1", cost: "" }); }}>Add line</Button>
      </div>
      {lines.length > 0 && (
        <div className="mb-4 space-y-1 text-sm">
          {lines.map((l, i) => <p key={i}>{l.qty} × {l.description || variants.find((v) => v.variant_id === l.variant_id)?.product_name} @ {formatINR(l.unit_cost_paise)}</p>)}
          <Button disabled={!draft.supplier_id || act.busy} onClick={async () => {
            await act.run(() => post("/purchases/orders", { supplier_id: draft.supplier_id, items: lines }), "Purchase order drafted.");
            setLines([]); void pos.reload(); }}>Save purchase order</Button>
        </div>
      )}
      <Table rows={pos.data ?? []} rowKey={(p) => p.id} empty="No purchase orders yet. Make one here or from AI tools → What to buy." columns={[
        { key: "n", label: "PO", render: (p) => <div><p className="font-medium">{p.po_no}</p><p className="text-xs text-gray-500">{p.supplier} · {formatDate(p.created_at)}</p></div> },
        { key: "i", label: "Items", render: (p) => p.items.map((i) => `${i.qty}× ${i.description}`).join(", ") },
        { key: "t", label: "Value", align: "right", render: (p) => <Money paise={p.total_paise} /> },
        { key: "s", label: "Status", render: (p) => <Badge tone={p.status === "RECEIVED" ? "good" : p.status === "CANCELLED" ? "bad" : "warn"}>{p.status}</Badge> },
        { key: "a", label: "", render: (p) => <div className="flex gap-1">
          {p.status === "DRAFT" && <Button className="!min-h-9" variant="secondary" onClick={async () => { await act.run(() => post(`/purchases/orders/${p.id}/status`, { status: "SENT" })); void pos.reload(); }}>Mark sent</Button>}
          {["DRAFT", "SENT"].includes(p.status) && <Button className="!min-h-9" onClick={() => { setReceiving(p); setQty(Object.fromEntries(p.items.map((i) => [i.id, String(i.qty - i.received_qty)]))); }}>Receive</Button>}
          {["DRAFT", "SENT"].includes(p.status) && <Button className="!min-h-9" variant="ghost" onClick={async () => { await act.run(() => post(`/purchases/orders/${p.id}/status`, { status: "CANCELLED" })); void pos.reload(); }}>Cancel</Button>}
        </div> },
      ]} />
      <Modal open={receiving !== null} title={`Receive ${receiving?.po_no}`} onClose={() => setReceiving(null)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Supplier bill no."><Input value={bill.no} onChange={(e) => setBill({ ...bill, no: e.target.value })} /></Field>
            <Field label="Bill date"><Input type="date" value={bill.date} onChange={(e) => setBill({ ...bill, date: e.target.value })} /></Field>
          </div>
          {receiving?.items.map((i) => (
            <div key={i.id} className="flex items-center gap-2 text-sm"><span className="flex-1">{i.description}{!i.variant_id && " (add it in Products first)"}</span>
              <Input className="w-20" inputMode="numeric" value={qty[i.id] ?? ""} onChange={(e) => setQty({ ...qty, [i.id]: e.target.value })} /></div>
          ))}
          <Button disabled={!bill.no || act.busy} onClick={async () => {
            const items = (receiving?.items ?? []).filter((i) => i.variant_id && Number(qty[i.id]) > 0).map((i) => ({ po_item_id: i.id, qty: Number(qty[i.id]) }));
            const r = await act.run(() => post(`/purchases/orders/${receiving!.id}/receive`, { supplier_bill_no: bill.no, bill_date: bill.date, items }), "Received. Stock added.");
            if (r) { setReceiving(null); void pos.reload(); onReceived(); } }}>Receive into stock</Button>
        </div>
      </Modal>
    </Card>
  );
}
