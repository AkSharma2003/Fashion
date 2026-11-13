import { useMemo, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Table } from "../../components/ui";
import { api } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate } from "../../lib/money";

type StockRow = { variant_id: string; product_name: string; category: string; sku: string; size: string | null;
  color: string | null; price_paise: number; on_hand: number; reserved: number; available: number;
  shop_id: string; shop: string | null };
type Movement = { id: string; quantity_delta: number; movement_type: string; source: string | null; reason: string | null; created_at: string };

export default function InventoryPage() {
  const { me, shops, shopId } = useStaff();
  const shopName = (id: string) => shops.find((s) => s.id === id)?.name ?? "—";
  const stock = useApi(() => api<StockRow[]>("/inventory/stock"));
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<StockRow | null>(null);
  const rows = useMemo(() => (stock.data ?? []).filter((r) =>
    `${r.product_name} ${r.sku} ${r.category} ${r.color ?? ""}`.toLowerCase().includes(q.toLowerCase())), [stock.data, q]);

  return (
    <Page title="Stock" crumb="Stock" actions={<Input placeholder="Search item / SKU" value={q} onChange={(e) => setQ(e.target.value)} className="w-56" />}>
      <p className="text-sm text-gray-600">
        {shopId === "all" && !me?.shop_id ? "Every shop's stock, one row per shop. " : `Stock of ${shopName(me?.shop_id ?? shopId)}. `}
        The website sells from all shops. "Reserved" is held by unpaid website orders.</p>
      <Card>
        {stock.loading && !stock.data && <Loading />}
        <Alert>{stock.error}</Alert>
        <Table rows={rows} rowKey={(r) => `${r.variant_id}:${r.shop_id}`} onRowClick={setSel} empty="No items yet. Add products and variants first." columns={[
          { key: "n", label: "Item", render: (r) => <div><p className="font-medium">{r.product_name}</p><p className="text-xs text-gray-500">{r.sku} · {[r.size, r.color].filter(Boolean).join(" / ")}</p></div> },
          { key: "s", label: "Shop", render: (r) => <span title={shopName(r.shop_id)}>{shopName(r.shop_id)}</span> },
          { key: "c", label: "Category", render: (r) => r.category },
          { key: "p", label: "Price", align: "right", render: (r) => <Money paise={r.price_paise} /> },
          { key: "o", label: "On hand", align: "right", render: (r) => <span className={r.on_hand < 0 ? "font-semibold text-[#D93025]" : ""}>{r.on_hand}</span> },
          { key: "r", label: "Reserved", align: "right", render: (r) => r.reserved },
          { key: "a", label: "Available", align: "right", render: (r) => r.available <= 0 ? <Badge tone="bad">{String(r.available)}</Badge> : r.available <= 1 ? <Badge tone="warn">{String(r.available)}</Badge> : r.available },
        ]} />
      </Card>
      {sel && <StockModal row={sel} canEdit={hasRole(me, "Manager")} onClose={() => { setSel(null); void stock.reload(); }} />}
    </Page>
  );
}

function StockModal({ row, canEdit, onClose }: { row: StockRow; canEdit: boolean; onClose: () => void }) {
  const history = useApi(() => api<Movement[]>(`/inventory/stock/${row.variant_id}/movements?shop_id=${row.shop_id}`), [row.variant_id]);
  const act = useAction();
  const [delta, setDelta] = useState("");
  const [counted, setCounted] = useState("");
  const [reason, setReason] = useState("");

  return (
    <Modal open title={`${row.product_name} (${row.sku}) · ${row.shop ?? ""}`} onClose={onClose} wide>
      <div className="space-y-4">
        <Alert tone="good">{act.notice}</Alert><Alert>{act.error}</Alert>
        {canEdit && (
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Reason (required)"><Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Damaged, found, counted…" /></Field>
            <Field label="Add / remove (e.g. -2)">
              <div className="flex gap-2"><Input inputMode="numeric" value={delta} onChange={(e) => setDelta(e.target.value)} />
                <Button disabled={act.busy || !reason || !Number(delta)} onClick={async () => {
                  await act.run(() => api("/inventory/stock/adjustments", { method: "POST", body: JSON.stringify({ variant_id: row.variant_id, shop_id: row.shop_id, quantity_delta: Number(delta), reason }) }), "Stock adjusted.");
                  setDelta(""); void history.reload(); }}>Save</Button></div>
            </Field>
            <Field label="Physical count">
              <div className="flex gap-2"><Input inputMode="numeric" value={counted} onChange={(e) => setCounted(e.target.value)} />
                <Button disabled={act.busy || !reason || counted === ""} onClick={async () => {
                  await act.run(() => api("/inventory/stock/counts", { method: "POST", body: JSON.stringify({ variant_id: row.variant_id, shop_id: row.shop_id, counted_quantity: Number(counted), reason }) }), "Count saved.");
                  setCounted(""); void history.reload(); }}>Save</Button></div>
            </Field>
          </div>
        )}
        <Card title="Stock history">
          {history.loading && <Loading />}
          <Table rows={history.data ?? []} rowKey={(m) => m.id} empty="No movements." columns={[
            { key: "d", label: "When", render: (m) => formatDate(m.created_at, true) },
            { key: "t", label: "Type", render: (m) => <span>{m.movement_type.replace(/_/g, " ")} <span className="text-xs text-gray-500">{m.source}</span></span> },
            { key: "r", label: "Reason", render: (m) => m.reason ?? "—" },
            { key: "q", label: "Qty", align: "right", render: (m) => <span className={m.quantity_delta < 0 ? "text-[#D93025]" : "text-[#1E8E3E]"}>{m.quantity_delta > 0 ? "+" : ""}{m.quantity_delta}</span> },
          ]} />
        </Card>
      </div>
    </Modal>
  );
}

