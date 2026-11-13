import { useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Money, Page, Select, Stat, Table } from "../../components/ui";
import { api, apiData, patch, post } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";

type Reorder = { variant_id: string; name: string; sku: string; size: string | null; color: string | null; available: number;
  forecast_units: Record<string, number>; confidence: string; qty: number; unit_cost_paise: number; budget_paise: number;
  cost_is_estimate: boolean; reorder_advice: { reason: string } };
type WhatToBuy = { reorder: Reorder[]; missing_products: { what: string; times_asked: number }[];
  trending_categories: { category: string; growth: number; sold_14d: number }[]; total_budget_paise: number;
  summary: string | null; summary_source: string };
type Forecast = { variant_id: string; name: string; sku: string; size: string | null; color: string | null; available: number;
  forecast_units: Record<string, number>; confidence: string; basis: string; reorder_advice: { suggested_units: number; reason: string } };
type Trends = { trending: { product_id: string; name: string; category: string; sold_14d: number; growth: number }[];
  categories: { category: string; sold_14d: number; growth: number }[] };

const TABS = [["buy", "What to buy"], ["forecast", "Forecast & trends"], ["describe", "Descriptions"], ["poster", "Poster maker"],
  ["requests", "Customer requests"], ["usage", "AI usage"]] as const;
// Who works with each tab (Owner/Admin see all): buying for managers and accounts, content for managers and online staff.
const TAB_ROLES: Record<string, string[]> = {
  buy: ["Manager", "Accountant"], forecast: ["Manager", "Accountant"], requests: ["Manager", "Accountant"],
  describe: ["Manager", "OnlineStaff"], poster: ["Manager", "OnlineStaff"], usage: [],
};

export default function AiToolsPage() {
  const { me } = useStaff();
  const visible = TABS.filter(([k]) => hasRole(me, ...TAB_ROLES[k]));
  const [picked, setTab] = useState<(typeof TABS)[number][0] | null>(null);
  const tab = picked && visible.some(([k]) => k === picked) ? picked : visible[0]?.[0];
  return (
    <Page title="AI tools" crumb="Buying intelligence and content" actions={
      <div className="flex flex-wrap gap-2">{visible.map(([k, l]) => <Button key={k} variant={k === tab ? "primary" : "secondary"} onClick={() => setTab(k)}>{l}</Button>)}</div>}>
      <p className="text-sm text-gray-600">Suggestions come from your own sales, stock and customer requests. Check everything before buying or publishing.</p>
      {tab === "buy" && <WhatToBuyTab />}
      {tab === "forecast" && <ForecastTab />}
      {tab === "describe" && <DescribeTab />}
      {tab === "poster" && <PosterTab />}
      {tab === "requests" && <RequestsTab />}
      {tab === "usage" && <UsageTab />}
    </Page>
  );
}

function WhatToBuyTab() {
  const data = useApi(() => apiData<WhatToBuy>("/ai/what-to-buy"));
  const suppliers = useApi(() => apiData<{ id: string; name: string }[]>("/purchases/suppliers"));
  const act = useAction();
  const [picked, setPicked] = useState<Record<string, boolean>>({});
  const [supplier, setSupplier] = useState("");
  const d = data.data;
  return (
    <>
      {data.loading && <Loading what="Working out what to buy" />}
      <Alert>{data.error || act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      {d && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Items to reorder" value={d.reorder.length} />
            <Stat label="Budget needed" value={formatINR(d.total_budget_paise)} note="at last purchase cost" />
            <Stat label="Products customers asked for" value={d.missing_products.length} />
          </div>
          {d.summary && <Card title="Summary"><p className="whitespace-pre-line text-sm">{d.summary}</p><p className="mt-2 text-xs text-gray-500">Written by AI from the numbers below.</p></Card>}
          <Card title="Reorder" actions={
            <div className="flex flex-wrap gap-2">
              <Select className="w-48" value={supplier} onChange={(e) => setSupplier(e.target.value)}>
                <option value="">Supplier…</option>{(suppliers.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select>
              <Button disabled={!supplier || act.busy} onClick={() => void act.run(() => post("/purchases/orders/from-suggestions", {
                supplier_id: supplier, variant_ids: Object.keys(picked).filter((k) => picked[k]).length ? Object.keys(picked).filter((k) => picked[k]) : null }),
                "Purchase order drafted. Open Purchasing to send it.")}>Make purchase order</Button>
            </div>}>
            <Table rows={d.reorder} rowKey={(r) => r.variant_id} empty="Nothing to reorder right now." columns={[
              { key: "c", label: "", render: (r) => <input type="checkbox" checked={Boolean(picked[r.variant_id])} onChange={(e) => setPicked({ ...picked, [r.variant_id]: e.target.checked })} /> },
              { key: "n", label: "Item", render: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-gray-500">{r.sku} {[r.size, r.color].filter(Boolean).join(" / ")}</p></div> },
              { key: "a", label: "In stock", align: "right", render: (r) => r.available },
              { key: "f", label: "Need in 30 days", align: "right", render: (r) => <span>{r.forecast_units["30"]} <Badge tone={r.confidence === "high" ? "good" : r.confidence === "medium" ? "warn" : "info"}>{r.confidence}</Badge></span> },
              { key: "q", label: "Buy", align: "right", render: (r) => <b>{r.qty}</b> },
              { key: "b", label: "Budget", align: "right", render: (r) => <span><Money paise={r.budget_paise} />{r.cost_is_estimate && <span className="block text-xs text-gray-500">cost estimated</span>}</span> },
            ]} />
          </Card>
          <div className="grid gap-6 xl:grid-cols-2">
            <Card title="Customers asked for (not in stock)">
              <Table rows={d.missing_products} rowKey={(m) => m.what} empty="No requests in the last 60 days." columns={[
                { key: "w", label: "What", render: (m) => m.what }, { key: "n", label: "Times", align: "right", render: (m) => m.times_asked }]} />
            </Card>
            <Card title="Category trend (last 14 days)">
              <Table rows={d.trending_categories} rowKey={(c) => c.category} empty="Not enough sales yet." columns={[
                { key: "c", label: "Category", render: (c) => c.category }, { key: "s", label: "Sold", align: "right", render: (c) => c.sold_14d },
                { key: "g", label: "Speed vs before", align: "right", render: (c) => <Badge tone={c.growth >= 1.2 ? "good" : c.growth < 0.8 ? "bad" : "info"}>{`${c.growth}x`}</Badge> }]} />
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function ForecastTab() {
  const f = useApi(() => apiData<Forecast[]>("/ai/forecast"));
  const tr = useApi(() => apiData<Trends>("/ai/trends"));
  const [q, setQ] = useState("");
  const rows = (f.data ?? []).filter((r) => `${r.name} ${r.sku}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <Card title="Trending now (sold 1.5x faster than before)">
        <Table rows={tr.data?.trending ?? []} rowKey={(t) => t.product_id} empty="Nothing is trending yet." columns={[
          { key: "n", label: "Product", render: (t) => t.name }, { key: "c", label: "Category", render: (t) => t.category },
          { key: "s", label: "Sold 14 days", align: "right", render: (t) => t.sold_14d }, { key: "g", label: "Growth", align: "right", render: (t) => `${t.growth}x` }]} />
      </Card>
      <Card title="Demand forecast" actions={<Input placeholder="Filter" value={q} onChange={(e) => setQ(e.target.value)} className="w-48" />}>
        {f.loading && <Loading />}
        <Table rows={rows} rowKey={(r) => r.variant_id} empty="No items." columns={[
          { key: "n", label: "Item", render: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-gray-500">{r.sku} · {r.basis}</p></div> },
          { key: "a", label: "Stock", align: "right", render: (r) => r.available },
          { key: "7", label: "7 days", align: "right", render: (r) => r.forecast_units["7"] },
          { key: "30", label: "30 days", align: "right", render: (r) => r.forecast_units["30"] },
          { key: "90", label: "90 days", align: "right", render: (r) => r.forecast_units["90"] },
          { key: "c", label: "Confidence", render: (r) => <Badge tone={r.confidence === "high" ? "good" : r.confidence === "medium" ? "warn" : "info"}>{r.confidence}</Badge> },
          { key: "r", label: "Advice", render: (r) => <span className="text-xs">{r.reorder_advice.suggested_units ? `buy ${r.reorder_advice.suggested_units}; ` : ""}{r.reorder_advice.reason}</span> },
        ]} />
      </Card>
    </>
  );
}

function DescribeTab() {
  const products = useApi(() => api<{ id: string; name: string; description: string | null }[]>("/catalog/"));
  const act = useAction();
  const [pid, setPid] = useState("");
  const [notes, setNotes] = useState("");
  const [lang, setLang] = useState("english");
  const [draft, setDraft] = useState<{ title: string; description: string; tags: string[]; source: string } | null>(null);
  return (
    <Card title="Description writer">
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Product"><Select value={pid} onChange={(e) => { setPid(e.target.value); setDraft(null); }}>
          <option value="">Choose…</option>{(products.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
        <Field label="Notes (fabric, work, occasion)"><Input value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <Field label="Language"><Select value={lang} onChange={(e) => setLang(e.target.value)}><option value="english">English</option><option value="hinglish">Hinglish</option><option value="hindi">Hindi</option></Select></Field>
        <div className="flex items-end"><Button disabled={!pid || act.busy} onClick={async () => setDraft((await act.run(() => post("/ai/describe", { product_id: pid, notes, language: lang }))) ?? null)}>Write</Button></div>
      </div>
      <div className="mt-3"><Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert></div>
      {draft && (
        <div className="mt-4 space-y-3">
          {draft.source !== "ai" && <Alert tone="warn">AI is not available; a simple draft from the product details is shown.</Alert>}
          <Field label="Title"><Input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></Field>
          <Field label="Description"><textarea value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            className="min-h-40 w-full rounded-md border border-gray-300 p-3" /></Field>
          <p className="text-sm">Tags: {draft.tags.join(", ")}</p>
          <Button disabled={act.busy} onClick={() => void act.run(() => api(`/catalog/${pid}`, { method: "PATCH", body: JSON.stringify({ name: draft.title, description: draft.description }) }),
            "Saved to the product. Check it on the website.")}>Use this text</Button>
        </div>
      )}
    </Card>
  );
}

function PosterTab() {
  const products = useApi(() => api<{ id: string; name: string }[]>("/catalog/"));
  const act = useAction();
  const [form, setForm] = useState({ headline: "", subline: "", footer: "", theme: "festive", size: "square", brief: "" });
  const [ids, setIds] = useState<string[]>([]);
  const [options, setOptions] = useState<{ headline: string; subline: string }[]>([]);
  const [svg, setSvg] = useState("");

  async function download(kind: "svg" | "png") {
    const name = `wearverse-poster.${kind}`;
    if (kind === "svg") {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      Object.assign(document.createElement("a"), { href: url, download: name }).click();
      return;
    }
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const canvas = Object.assign(document.createElement("canvas"), { width: img.width, height: img.height });
      canvas.getContext("2d")!.drawImage(img, 0, 0);
      try {
        Object.assign(document.createElement("a"), { href: canvas.toDataURL("image/png"), download: name }).click();
      } catch {
        act.setError("PNG blocked by the photo server's settings; download SVG instead.");
      }
    };
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
      <Card title="Poster details">
        <div className="space-y-3">
          <Field label="Idea for AI suggestions (optional)" hint="e.g. Diwali sale on silk sarees, 20% off till 5 Nov">
            <div className="flex gap-2"><Input value={form.brief} onChange={(e) => setForm({ ...form, brief: e.target.value })} />
              <Button variant="secondary" disabled={form.brief.length < 3 || act.busy} onClick={async () => {
                const r = await act.run(() => post<{ options: { headline: string; subline: string }[] }>("/ai/poster/copy", { brief: form.brief }));
                if (r) setOptions(r.options); }}>Suggest</Button></div>
          </Field>
          {options.map((o, i) => <button key={i} type="button" className="block w-full rounded border border-gray-200 p-2 text-left text-sm hover:bg-gray-50"
            onClick={() => setForm({ ...form, headline: o.headline, subline: o.subline })}><b>{o.headline}</b><br />{o.subline}</button>)}
          <Field label="Headline (printed exactly)"><Input value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} /></Field>
          <Field label="Second line"><Input value={form.subline} onChange={(e) => setForm({ ...form, subline: e.target.value })} /></Field>
          <Field label="Footer (address, phone, dates)"><Input value={form.footer} onChange={(e) => setForm({ ...form, footer: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Style"><Select value={form.theme} onChange={(e) => setForm({ ...form, theme: e.target.value })}>
              <option value="festive">Festive</option><option value="wedding">Wedding</option><option value="sale">Sale</option><option value="fresh">Fresh</option></Select></Field>
            <Field label="Shape"><Select value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })}>
              <option value="square">Square (post)</option><option value="story">Story</option><option value="banner">Website banner</option></Select></Field>
          </div>
          <Field label="Product photos (up to 3)">
            <Select multiple value={ids} onChange={(e) => setIds(Array.from(e.target.selectedOptions).map((o) => o.value).slice(0, 3))} className="!min-h-28">
              {(products.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select>
          </Field>
          <Button disabled={form.headline.length < 2 || act.busy} onClick={async () => {
            const r = await act.run(() => post<{ svg: string }>("/ai/poster", { ...form, footer: form.footer || null, product_ids: ids }));
            if (r) setSvg(r.svg); }}>Make poster</Button>
          <Alert>{act.error}</Alert>
        </div>
      </Card>
      <Card title="Preview" actions={svg && <div className="flex gap-2"><Button variant="secondary" onClick={() => void download("svg")}>Download SVG</Button><Button variant="secondary" onClick={() => void download("png")}>Download PNG</Button></div>}>
        {svg ? <div className="mx-auto max-w-xl [&>svg]:h-auto [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: svg }} /> : <p className="text-sm text-gray-500">The poster appears here. Check every word before sharing.</p>}
      </Card>
    </div>
  );
}

function RequestsTab() {
  const list = useApi(() => apiData<{ id: string; text: string; source: string; status: string; created_at: string }[]>("/ai/missing-requests"));
  const act = useAction();
  const [text, setText] = useState("");
  return (
    <Card title="What customers asked for" actions={
      <div className="flex gap-2"><Input placeholder="e.g. yellow haldi saree" value={text} onChange={(e) => setText(e.target.value)} className="w-56" />
        <Button disabled={text.length < 2} onClick={async () => { await act.run(() => post("/ai/missing-requests", { text })); setText(""); void list.reload(); }}>Add</Button></div>}>
      <p className="mb-3 text-sm text-gray-600">Searches with no results and chat questions are added here by themselves. Staff can add counter requests too.</p>
      <Alert>{act.error}</Alert>
      <Table rows={list.data ?? []} rowKey={(r) => r.id} empty="No open requests." columns={[
        { key: "t", label: "Request", render: (r) => r.text }, { key: "s", label: "From", render: (r) => <Badge tone="info">{r.source}</Badge> },
        { key: "d", label: "When", render: (r) => formatDate(r.created_at, true) },
        { key: "a", label: "", render: (r) => <div className="flex gap-2">
          <Button className="!min-h-9" variant="secondary" onClick={async () => { await act.run(() => patch(`/ai/missing-requests/${r.id}`, { status: "ordered" })); void list.reload(); }}>Ordered</Button>
          <Button className="!min-h-9" variant="ghost" onClick={async () => { await act.run(() => patch(`/ai/missing-requests/${r.id}`, { status: "ignored" })); void list.reload(); }}>Ignore</Button></div> },
      ]} />
    </Card>
  );
}

function UsageTab() {
  const usage = useApi(() => apiData<{ month_spend_paise: number; budget_paise: number; features: Record<string, boolean>;
    by_feature: { feature: string; source: string; calls: number; cost_paise: number }[] }>("/ai/usage"));
  const act = useAction();
  const [budget, setBudget] = useState("");
  const u = usage.data;
  return (
    <>
      {u && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Stat label="AI spend this month" value={formatINR(u.month_spend_paise)} note="estimated from tokens" tone={u.month_spend_paise >= u.budget_paise * 0.8 ? "warn" : undefined} />
          <Stat label="Monthly limit" value={formatINR(u.budget_paise)} note="AI falls back to normal features above this" />
          <Stat label="Calls this month" value={u.by_feature.reduce((s, r) => s + r.calls, 0)} />
        </div>
      )}
      <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      {u && (
        <Card title="Switches">
          <div className="flex flex-wrap gap-3">
            {Object.entries(u.features).map(([k, on]) => (
              <label key={k} className="flex items-center gap-2 rounded border border-gray-200 px-3 py-2 text-sm">
                <input type="checkbox" checked={on} onChange={async (e) => {
                  await act.run(() => patch("/settings", { ai_features: { ...u.features, [k]: e.target.checked } }), "Saved."); void usage.reload(); }} />{k}
              </label>
            ))}
          </div>
          <div className="mt-4 flex items-end gap-2">
            <Field label="Monthly limit ₹"><Input inputMode="decimal" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder={String(u.budget_paise / 100)} /></Field>
            <Button disabled={!rupeesToPaise(budget)} onClick={async () => { await act.run(() => patch("/settings", { ai_monthly_budget_paise: rupeesToPaise(budget) }), "Limit saved."); void usage.reload(); }}>Save</Button>
            <Button variant="secondary" onClick={() => void act.run(() => post("/ai/index/refresh"), "Search and photo index rebuilt.")}>Rebuild search index</Button>
          </div>
        </Card>
      )}
      <Card title="By feature">
        <Table rows={u?.by_feature ?? []} rowKey={(r) => r.feature + r.source} empty="No AI calls this month." columns={[
          { key: "f", label: "Feature", render: (r) => r.feature }, { key: "s", label: "Result", render: (r) => <Badge tone={r.source === "ai" ? "good" : "info"}>{r.source}</Badge> },
          { key: "c", label: "Calls", align: "right", render: (r) => r.calls }, { key: "m", label: "Cost", align: "right", render: (r) => <Money paise={r.cost_paise} /> }]} />
      </Card>
    </>
  );
}
