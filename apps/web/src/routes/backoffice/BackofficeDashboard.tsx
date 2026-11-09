import { Link } from "react-router-dom";
import { Alert, Badge, Button, Card, Loading, Money, Page, Stat, Table } from "../../components/ui";
import { apiData, post } from "../../lib/api/client";
import { useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR } from "../../lib/money";

type Dashboard = {
  today: { shop_sales_paise: number; bills: number; online_sales_paise: number; online_orders: number;
    collections_paise: number; by_mode: Record<string, number> };
  khata_outstanding_paise: number; orders_to_pack: number; fall_pico_open: number; fall_pico_late: number;
  low_stock_variants: number; tally_backlog: number; sync_issues: number;
  alerts: { id: string; kind: string; severity: string; message: string; created_at: string }[];
  recent_bills: { id: string; bill_no: string; total_paise: number; source: string; created_at: string }[];
};

export default function BackofficeDashboard() {
  const { data, error, loading, reload } = useApi(() => apiData<Dashboard>("/reports/dashboard"));

  return (
    <Page title="Today at the shop" crumb="Dashboard" actions={<Button variant="secondary" onClick={() => void reload()}>Refresh</Button>}>
      {loading && !data && <Loading />}
      <Alert>{error}</Alert>
      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Shop sales" value={formatINR(data.today.shop_sales_paise)} note={`${data.today.bills} bills`} />
            <Stat label="Website sales" value={formatINR(data.today.online_sales_paise)} note={`${data.today.online_orders} orders placed`} />
            <Stat label="Khata collected today" value={formatINR(data.today.collections_paise)} tone="good" />
            <Stat label="Khata outstanding" value={formatINR(data.khata_outstanding_paise)} tone="warn" note="Amount to collect" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Link to="/backoffice/online-orders"><Stat label="Orders to pack" value={data.orders_to_pack} /></Link>
            <Link to="/backoffice/fall-pico"><Stat label="Fall-pico open" value={data.fall_pico_open}
              note={data.fall_pico_late ? `${data.fall_pico_late} late` : "none late"} tone={data.fall_pico_late ? "bad" : undefined} /></Link>
            <Link to="/backoffice/inventory"><Stat label="Low stock (≤1 left)" value={data.low_stock_variants} tone={data.low_stock_variants ? "warn" : undefined} /></Link>
            <Link to="/backoffice/tally"><Stat label="Tally waiting / issues" value={`${data.tally_backlog} / ${data.sync_issues}`}
              tone={data.sync_issues ? "bad" : data.tally_backlog ? "warn" : "good"} /></Link>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card title="Alerts">
              {data.alerts.length === 0 ? <p className="text-sm text-gray-500">No open alerts.</p> : (
                <ul className="space-y-3">
                  {data.alerts.map((a) => (
                    <li key={a.id} className="flex items-start justify-between gap-3 border-b border-gray-100 pb-3 last:border-0">
                      <div>
                        <Badge tone={a.severity === "critical" ? "bad" : "warn"}>{a.kind}</Badge>
                        <p className="mt-1 text-sm">{a.message}</p>
                        <p className="text-xs text-gray-500">{formatDate(a.created_at, true)}</p>
                      </div>
                      <Button variant="secondary" onClick={async () => { await post(`/reports/alerts/${a.id}/resolve`); void reload(); }}>Done</Button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Today by payment mode">
              {Object.keys(data.today.by_mode).length === 0 ? <p className="text-sm text-gray-500">No bills yet today.</p> : (
                <ul className="space-y-2 text-sm">
                  {Object.entries(data.today.by_mode).map(([mode, amount]) => (
                    <li key={mode} className="flex justify-between"><span>{mode}</span><Money paise={amount} /></li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title="Latest bills" actions={<Link className="text-sm underline" to="/backoffice/bills">All bills</Link>}>
            <Table rows={data.recent_bills} rowKey={(b) => b.id} empty="No bills yet." columns={[
              { key: "no", label: "Bill", render: (b) => <span className="font-medium">{b.bill_no}</span> },
              { key: "src", label: "Made in", render: (b) => <Badge>{b.source === "tally_import" ? "Tally" : "POS"}</Badge> },
              { key: "at", label: "Time", render: (b) => formatDate(b.created_at, true) },
              { key: "total", label: "Total", align: "right", render: (b) => <Money paise={b.total_paise} /> },
            ]} />
          </Card>
        </>
      )}
    </Page>
  );
}
