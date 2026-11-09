import { useState } from "react";
import { Alert, Card, Input, Loading, Money, Page, Stat, Table } from "../../components/ui";
import { apiData } from "../../lib/api/client";
import { useApi } from "../../lib/hooks/useApi";
import { formatINR } from "../../lib/money";

type Sales = { shop: { date: string; source: string; bills: number; total_paise: number; returned_paise: number }[];
  online: { date: string; orders: number; total_paise: number }[]; top_products: { name: string; qty: number; total_paise: number }[] };
type Gst = { shop_by_rate: { rate_percent: number; hsn: string | null; taxable_paise: number; cgst_paise: number; sgst_paise: number; total_paise: number }[];
  online_tax_paise: number; note: string };
type Ageing = { totals: Record<string, number> };

export default function ReportsPage() {
  const today = new Date();
  const first = new Date(today.getFullYear(), today.getMonth(), 1);
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const [range, setRange] = useState({ from: iso(first), to: iso(today) });
  const q = `date_from=${range.from}&date_to=${range.to}`;
  const sales = useApi(() => apiData<Sales>(`/reports/sales?${q}`), [q]);
  const gst = useApi(() => apiData<Gst>(`/reports/gst?${q}`), [q]);
  const ageing = useApi(() => apiData<Ageing>("/khata/reports/ageing"));
  const shopTotal = (sales.data?.shop ?? []).reduce((s, r) => s + r.total_paise - r.returned_paise, 0);
  const onlineTotal = (sales.data?.online ?? []).reduce((s, r) => s + r.total_paise, 0);

  return (
    <Page title="Reports" crumb="Owner & accountant" actions={<>
      <Input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} className="w-40" />
      <Input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} className="w-40" /></>}>
      <Alert>{sales.error || gst.error}</Alert>
      {sales.loading && <Loading />}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Shop sales (net of returns)" value={formatINR(shopTotal)} />
        <Stat label="Website sales" value={formatINR(onlineTotal)} />
        <Stat label="Khata outstanding" value={formatINR(ageing.data?.totals.total)} tone="warn" />
        <Stat label="Khata overdue" value={formatINR(ageing.data?.totals.overdue)} tone="bad" />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Sales by day">
          <Table rows={sales.data?.shop ?? []} rowKey={(r) => r.date + r.source} empty="No sales in this period." columns={[
            { key: "d", label: "Day", render: (r) => r.date },
            { key: "s", label: "Made in", render: (r) => (r.source === "tally_import" ? "Tally" : "POS") },
            { key: "b", label: "Bills", align: "right", render: (r) => r.bills },
            { key: "t", label: "Total", align: "right", render: (r) => <Money paise={r.total_paise - r.returned_paise} /> },
          ]} />
        </Card>
        <Card title="Top products">
          <Table rows={sales.data?.top_products ?? []} rowKey={(r) => r.name} empty="—" columns={[
            { key: "n", label: "Product", render: (r) => r.name },
            { key: "q", label: "Qty", align: "right", render: (r) => r.qty },
            { key: "t", label: "Sales", align: "right", render: (r) => <Money paise={r.total_paise} /> },
          ]} />
        </Card>
        <Card title="GST (shop bills)">
          <Table rows={gst.data?.shop_by_rate ?? []} rowKey={(r) => `${r.rate_percent}-${r.hsn}`} empty="—" columns={[
            { key: "r", label: "Rate / HSN", render: (r) => `${r.rate_percent}% · ${r.hsn ?? "—"}` },
            { key: "x", label: "Taxable", align: "right", render: (r) => <Money paise={r.taxable_paise} /> },
            { key: "c", label: "CGST", align: "right", render: (r) => <Money paise={r.cgst_paise} /> },
            { key: "s", label: "SGST", align: "right", render: (r) => <Money paise={r.sgst_paise} /> },
          ]} />
          <p className="mt-3 text-xs text-gray-500">Website GST: {formatINR(gst.data?.online_tax_paise)}. {gst.data?.note}</p>
        </Card>
        <Card title="Khata ageing">
          <ul className="space-y-2 text-sm">
            {[["0_30", "0–30 days"], ["31_60", "31–60 days"], ["61_90", "61–90 days"], ["90_plus", "Over 90 days"]].map(([k, l]) => (
              <li key={k} className="flex justify-between"><span>{l}</span><Money paise={ageing.data?.totals[k]} /></li>))}
          </ul>
        </Card>
      </div>
    </Page>
  );
}
