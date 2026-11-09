import { useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Money, Page, Select, Stat, Table } from "../../components/ui";
import { api, apiData, post } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate, rupeesToPaise } from "../../lib/money";

type Overview = { mode: string; cutover_date: string | null; pos_mode: string | null; agent_last_seen: { at: string } | null;
  pending: number; errors: number; open_issues: number; synced_last_24h: number; oldest_pending_at: string | null; agent_key_configured: boolean };
type Issue = { id: string; direction: string; reason_code: string; message: string; created_at: string };
type OutboxRow = { id: string; event_type: string; reference: string; status: string; attempts: number; last_error: string | null; amount: string | null; created_at: string };
type Recon = { id: string; date: string; status: string; wearverse: Record<string, number>; tally: Record<string, number> | null;
  differences: { field: string; wearverse: number; tally: number; difference: number }[] };

export default function TallyPage() {
  const [tab, setTab] = useState<"status" | "issues" | "recon" | "mapping">("status");
  return (
    <Page title="Tally" crumb="Accounts sync" actions={
      <div className="flex flex-wrap gap-2">{([["status", "Sync status"], ["issues", "Sync issues"], ["recon", "Reconciliation"], ["mapping", "Mapping"]] as const).map(([k, l]) =>
        <Button key={k} variant={tab === k ? "primary" : "secondary"} onClick={() => setTab(k)}>{l}</Button>)}</div>}>
      {tab === "status" && <Status />}
      {tab === "issues" && <Issues />}
      {tab === "recon" && <Reconciliation />}
      {tab === "mapping" && <Mapping />}
    </Page>
  );
}

function Status() {
  const { me } = useStaff();
  const ov = useApi(() => apiData<Overview>("/tally/overview"));
  const out = useApi(() => apiData<OutboxRow[]>("/tally/outbox"));
  const act = useAction();
  const [mode, setMode] = useState({ mode: "A", pos_mode: "parallel", cutover_date: "" });
  const o = ov.data;
  const lastSeen = o?.agent_last_seen?.at ? (Date.now() - new Date(o.agent_last_seen.at).getTime()) / 60000 : null;

  return (
    <>
      {ov.loading && <Loading />}
      <Alert>{ov.error}</Alert>
      {o && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Mode" value={o.mode === "B" ? "B · POS bills" : "A · Tally bills"} note={`POS: ${o.pos_mode ?? (o.mode === "B" ? "live" : "parallel")}${o.cutover_date ? ` · cutover ${o.cutover_date}` : ""}`} />
          <Stat label="Agent" value={lastSeen === null ? "Never seen" : lastSeen < 2 ? "Online" : `${Math.round(lastSeen)} min ago`}
            tone={lastSeen !== null && lastSeen < 2 ? "good" : "bad"} note={o.agent_key_configured ? "Key set" : "TALLY_AGENT_API_KEY not set"} />
          <Stat label="Waiting for Tally" value={o.pending} note={o.oldest_pending_at ? `oldest ${formatDate(o.oldest_pending_at, true)}` : "none"} tone={o.pending ? "warn" : "good"} />
          <Stat label="Errors / issues" value={`${o.errors} / ${o.open_issues}`} tone={o.errors || o.open_issues ? "bad" : "good"} note={`${o.synced_last_24h} synced in 24 h`} />
        </div>
      )}
      {hasRole(me) && (
        <Card title="Billing mode (owner)">
          <p className="mb-3 text-sm text-gray-600">Mode A: the counter bills in TallyPrime and WearVerse imports. During the parallel run the POS saves bills for comparison only. Mode B: the POS is live and WearVerse sends sales to Tally. Only one mode is active, so a sale is never entered twice.</p>
          <div className="grid gap-3 sm:grid-cols-4">
            <Field label="Mode"><Select value={mode.mode} onChange={(e) => setMode({ ...mode, mode: e.target.value, pos_mode: e.target.value === "B" ? "live" : "parallel" })}>
              <option value="A">A · bill in Tally</option><option value="B">B · bill in WearVerse POS</option></Select></Field>
            <Field label="POS"><Select value={mode.pos_mode} onChange={(e) => setMode({ ...mode, pos_mode: e.target.value })}>
              {mode.mode === "A" ? <><option value="parallel">Parallel run</option><option value="off">Off</option></> : <option value="live">Live</option>}</Select></Field>
            <Field label="Cutover date"><Input type="date" value={mode.cutover_date} onChange={(e) => setMode({ ...mode, cutover_date: e.target.value })} /></Field>
            <div className="flex items-end"><Button disabled={act.busy} onClick={async () => {
              if (!window.confirm(`Switch to Mode ${mode.mode}?`)) return;
              await act.run(() => post("/tally/mode", { ...mode, cutover_date: mode.cutover_date || null }), "Mode saved."); void ov.reload(); }}>Save</Button></div>
          </div>
          <div className="mt-2"><Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert></div>
        </Card>
      )}
      <Card title="Vouchers to Tally">
        <Table rows={out.data ?? []} rowKey={(r) => r.id} empty="Nothing sent yet." columns={[
          { key: "r", label: "Reference", render: (r) => <div><p className="font-medium">{r.reference.replace("tally:", "")}</p><p className="text-xs text-gray-500">{r.event_type.replace(/_/g, " ")}</p></div> },
          { key: "d", label: "Queued", render: (r) => formatDate(r.created_at, true) },
          { key: "a", label: "Amount", align: "right", render: (r) => r.amount ? <Money paise={rupeesToPaise(r.amount)} /> : "—" },
          { key: "s", label: "Status", render: (r) => <div><Badge>{r.status}</Badge>{r.last_error && <p className="mt-1 max-w-xs text-xs text-[#D93025]">{r.last_error}</p>}</div> },
        ]} />
      </Card>
    </>
  );
}

function Issues() {
  const issues = useApi(() => apiData<Issue[]>("/tally/issues"));
  const act = useAction();
  return (
    <Card title="Open sync issues">
      <p className="mb-3 text-sm text-gray-600">Fix the cause (for example map the party ledger or stock item), then press Retry. In Mode A an unmatched khata bill sends no WhatsApp until it is fixed.</p>
      <Alert>{act.error || issues.error}</Alert><Alert tone="good">{act.notice}</Alert>
      <Table rows={issues.data ?? []} rowKey={(i) => i.id} empty="No open issues." columns={[
        { key: "c", label: "Problem", render: (i) => <div><Badge tone="bad">{i.reason_code}</Badge><p className="mt-1 text-sm">{i.message}</p></div> },
        { key: "d", label: "Since", render: (i) => formatDate(i.created_at, true) },
        { key: "a", label: "", render: (i) => <div className="flex gap-2">
          <Button className="!min-h-9" onClick={async () => { await act.run(() => post(`/tally/issues/${i.id}/retry`), "Retried."); void issues.reload(); }}>Retry</Button>
          <Button className="!min-h-9" variant="secondary" onClick={async () => {
            const note = window.prompt("Why can this be ignored?"); if (!note) return;
            await act.run(() => post(`/tally/issues/${i.id}/resolve`, { note })); void issues.reload(); }}>Ignore</Button></div> },
      ]} />
    </Card>
  );
}

function Reconciliation() {
  const runs = useApi(() => apiData<Recon[]>("/tally/reconciliation"));
  const act = useAction();
  const [day, setDay] = useState(() => new Date(Date.now() - 86400000).toISOString().slice(0, 10));
  const label: Record<string, string> = { sales_paise: "Sales", gst_paise: "GST", receipts_paise: "Receipts" };
  return (
    <Card title="WearVerse vs Tally, day totals" actions={<div className="flex gap-2">
      <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="w-44" />
      <Button disabled={act.busy} onClick={async () => { await act.run(() => post(`/tally/reconciliation/run?day=${day}`)); void runs.reload(); }}>Compare</Button></div>}>
      <Alert>{act.error}</Alert>
      <Table rows={runs.data ?? []} rowKey={(r) => r.id} empty="No comparisons yet. The nightly job runs automatically." columns={[
        { key: "d", label: "Day", render: (r) => formatDate(r.date) },
        { key: "s", label: "Result", render: (r) => <Badge>{r.status}</Badge> },
        { key: "w", label: "WearVerse sales", align: "right", render: (r) => <Money paise={r.wearverse.sales_paise} /> },
        { key: "t", label: "Tally sales", align: "right", render: (r) => r.tally ? <Money paise={r.tally.sales_paise} /> : "—" },
        { key: "x", label: "Differences", render: (r) => r.differences.map((d) => <p key={d.field} className="text-xs text-[#D93025]">{label[d.field] ?? d.field}: <Money paise={d.difference} /></p>) },
      ]} />
    </Card>
  );
}

function Mapping() {
  const items = useApi(() => apiData<{ mapped: { id: string; tally_stock_item: string; sku: string; product_name: string }[]; unmapped_from_issues: string[] }>("/tally/mappings/items"));
  const ledgers = useApi(() => apiData<{ id: string; kind: string; ledger_name: string; ref_id: string }[]>("/tally/mappings/ledgers"));
  const variants = useApi(() => api<{ variant_id: string; product_name: string; sku: string }[]>("/inventory/stock"));
  const accounts = useApi(() => apiData<{ accounts: { customer_id: string; customer_name: string; phone_number: string }[] }>("/khata/accounts"));
  const act = useAction();
  const [im, setIm] = useState({ tally_stock_item: "", variant_id: "" });
  const [lm, setLm] = useState({ kind: "customer", ledger_name: "", ref_id: "" });
  const kinds = ["customer", "sales", "cash", "upi", "card", "bank", "cgst", "sgst", "igst", "online", "purchase", "input_cgst", "input_sgst", "salary", "fall_pico_wages"];
  return (
    <>
      <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Stock items">
          {!!items.data?.unmapped_from_issues.length && <p className="mb-2 text-sm text-[#D93025]">Not matched yet: {items.data.unmapped_from_issues.join(", ")}</p>}
          <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <Input placeholder="Tally stock item name" value={im.tally_stock_item} onChange={(e) => setIm({ ...im, tally_stock_item: e.target.value })} />
            <Select value={im.variant_id} onChange={(e) => setIm({ ...im, variant_id: e.target.value })}>
              <option value="">WearVerse item…</option>{(variants.data ?? []).map((v) => <option key={v.variant_id} value={v.variant_id}>{v.product_name} · {v.sku}</option>)}</Select>
            <Button disabled={!im.tally_stock_item || !im.variant_id} onClick={async () => { await act.run(() => post("/tally/mappings/items", im), "Item mapped."); setIm({ tally_stock_item: "", variant_id: "" }); void items.reload(); }}>Map</Button>
          </div>
          <Table rows={items.data?.mapped ?? []} rowKey={(m) => m.id} empty="No items mapped." columns={[
            { key: "t", label: "Tally item", render: (m) => m.tally_stock_item },
            { key: "w", label: "WearVerse", render: (m) => `${m.product_name} · ${m.sku}` },
          ]} />
        </Card>
        <Card title="Ledgers">
          <div className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <Select value={lm.kind} onChange={(e) => setLm({ ...lm, kind: e.target.value, ref_id: "" })}>{kinds.map((k) => <option key={k}>{k}</option>)}</Select>
            <Input placeholder="Tally ledger name" value={lm.ledger_name} onChange={(e) => setLm({ ...lm, ledger_name: e.target.value })} />
            {lm.kind === "customer" ? (
              <Select value={lm.ref_id} onChange={(e) => setLm({ ...lm, ref_id: e.target.value })}>
                <option value="">Khata customer…</option>{(accounts.data?.accounts ?? []).map((a) => <option key={a.customer_id} value={a.customer_id}>{a.customer_name} · {a.phone_number}</option>)}</Select>
            ) : <span />}
            <Button disabled={!lm.ledger_name || (lm.kind === "customer" && !lm.ref_id)} onClick={async () => { await act.run(() => post("/tally/mappings/ledgers", lm), "Ledger mapped."); setLm({ ...lm, ledger_name: "", ref_id: "" }); void ledgers.reload(); }}>Map</Button>
          </div>
          <Table rows={ledgers.data ?? []} rowKey={(l) => l.id} empty="Defaults are used until you map ledgers." columns={[
            { key: "k", label: "Meaning", render: (l) => <Badge tone="info">{l.kind}</Badge> },
            { key: "n", label: "Tally ledger", render: (l) => l.ledger_name },
          ]} />
        </Card>
      </div>
    </>
  );
}
