import { useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Select, Table } from "../../components/ui";
import { apiData, post } from "../../lib/api/client";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate } from "../../lib/money";

export type BillItem = { id: string; product_name: string; sku: string | null; qty: number; unit_price_paise: number;
  discount_paise: number; line_total_paise: number; gst_rate_bp: number; returned_qty: number };
export type Bill = { id: string; bill_no: string; counter: string; source: string; shadow: boolean; status: string;
  customer: { id: string; name: string; phone: string } | null; total_paise: number; taxable_paise: number; cgst_paise: number;
  sgst_paise: number; discount_paise: number; returned_paise: number; items: BillItem[]; payments: { mode: string; amount_paise: number }[]; created_at: string };

export default function BillsPage() {
  const [q, setQ] = useState("");
  const bills = useApi(() => apiData<Bill[]>(`/pos/bills${q ? `?q=${encodeURIComponent(q)}` : ""}`));
  const [sel, setSel] = useState<Bill | null>(null);
  return (
    <Page title="Shop bills" crumb="Sales" actions={
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void bills.reload(); }}>
        <Input placeholder="Bill number" value={q} onChange={(e) => setQ(e.target.value)} className="w-48" />
        <Button type="submit" variant="secondary">Find</Button>
      </form>}>
      <Card>
        {bills.loading && !bills.data && <Loading />}
        <Alert>{bills.error}</Alert>
        <Table rows={bills.data ?? []} rowKey={(b) => b.id} onRowClick={setSel} empty="No bills yet." columns={[
          { key: "n", label: "Bill", render: (b) => <div><p className="font-medium">{b.bill_no}</p><p className="text-xs text-gray-500">{formatDate(b.created_at, true)}</p></div> },
          { key: "c", label: "Customer", render: (b) => b.customer?.name ?? "Walk-in" },
          { key: "s", label: "", render: (b) => <div className="flex flex-wrap gap-1">
            <Badge tone="info">{b.source === "tally_import" ? "Tally" : "POS"}</Badge>{b.shadow && <Badge tone="warn">parallel run</Badge>}
            {b.status !== "COMPLETED" && <Badge>{b.status}</Badge>}</div> },
          { key: "p", label: "Paid by", render: (b) => b.payments.map((p) => p.mode).join(" + ") },
          { key: "t", label: "Total", align: "right", render: (b) => <Money paise={b.total_paise} /> },
        ]} />
      </Card>
      {sel && <BillModal bill={sel} onClose={() => { setSel(null); void bills.reload(); }} />}
    </Page>
  );
}

export function BillModal({ bill, onClose }: { bill: Bill; onClose: () => void }) {
  const act = useAction();
  const [qty, setQty] = useState<Record<string, string>>({});
  const [mode, setMode] = useState(bill.payments.some((p) => p.mode === "KHATA") ? "KHATA" : "CASH");
  const [pin, setPin] = useState("");
  const [reason, setReason] = useState("");
  const canReturn = bill.source === "pos" && bill.status !== "RETURNED";

  return (
    <Modal open title={`Bill ${bill.bill_no}`} onClose={onClose} wide>
      <div className="space-y-4">
        <Table rows={bill.items} rowKey={(i) => i.id} columns={[
          { key: "n", label: "Item", render: (i) => <div>{i.product_name}<p className="text-xs text-gray-500">{i.sku} · GST {i.gst_rate_bp / 100}%</p></div> },
          { key: "q", label: "Qty", align: "right", render: (i) => `${i.qty}${i.returned_qty ? ` (−${i.returned_qty})` : ""}` },
          { key: "t", label: "Amount", align: "right", render: (i) => <Money paise={i.line_total_paise} /> },
          ...(canReturn ? [{ key: "r", label: "Return", render: (i: BillItem) => (
            <Select className="!min-h-9 w-20" value={qty[i.id] ?? "0"} onChange={(e) => setQty({ ...qty, [i.id]: e.target.value })}>
              {Array.from({ length: i.qty - i.returned_qty + 1 }, (_, n) => <option key={n}>{n}</option>)}
            </Select>) }] : []),
        ]} />
        <p className="text-right text-sm">Taxable <Money paise={bill.taxable_paise} /> · CGST <Money paise={bill.cgst_paise} /> · SGST <Money paise={bill.sgst_paise} /> · <b>Total <Money paise={bill.total_paise} /></b></p>
        {canReturn && (
          <Card title="Return / exchange">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Refund as"><Select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="CASH">Cash</option><option value="UPI">UPI</option><option value="KHATA">Khata credit</option><option value="EXCHANGE">Exchange</option></Select></Field>
              <Field label="Manager PIN" hint="Not needed if you are a manager"><Input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} /></Field>
              <Field label="Reason"><Input value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
            </div>
            <div className="mt-3 space-y-2"><Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
              <Button disabled={act.busy} onClick={async () => {
                const items = Object.entries(qty).filter(([, q]) => Number(q) > 0).map(([bill_item_id, q]) => ({ bill_item_id, qty: Number(q) }));
                if (!items.length) return act.setError("Choose what is being returned.");
                await act.run(() => post(`/pos/bills/${bill.id}/return`, { idempotency_key: crypto.randomUUID(), items,
                  refund_mode: mode, reason: reason || null, approval_pin: pin || null }), "Return saved. Stock is back.");
              }}>Save return</Button></div>
          </Card>
        )}
      </div>
    </Modal>
  );
}
