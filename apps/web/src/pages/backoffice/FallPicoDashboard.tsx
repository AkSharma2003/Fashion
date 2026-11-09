import { useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Select, Stat, Table } from "../../components/ui";
import { apiData, patch, post } from "../../lib/api/client";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";

type Job = { id: string; tag_code: string; status: string; source_type: string; source_label: string | null; product_name: string;
  worker_id: string | null; worker_name: string | null; promised_date: string | null; is_late: boolean; rework_count: number };
type Worker = { id: string; name: string; phone: string | null; rate_paise: number; capacity_per_day: number; is_active: boolean; balance_paise: number };
type Statement = { worker: Worker; jobs_done: number; earned_paise: number; paid_paise: number; advance_paise: number; balance_paise: number;
  entries: { id: string; type: string; amount_paise: number; running_balance_paise: number; note: string | null; created_at: string }[] };

const COLUMNS = ["PENDING", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "REWORK", "QC_PASSED", "READY"];
const NEXT: Record<string, { to: string; label: string; tone?: "danger" | "secondary" }[]> = {
  ASSIGNED: [{ to: "IN_PROGRESS", label: "Worker started" }, { to: "PENDING", label: "Unassign", tone: "secondary" }],
  IN_PROGRESS: [{ to: "COMPLETED", label: "Returned by worker" }],
  REWORK: [{ to: "IN_PROGRESS", label: "Back to worker" }],
  COMPLETED: [{ to: "QC_PASSED", label: "QC pass" }, { to: "REWORK", label: "QC fail → rework", tone: "danger" }],
  QC_PASSED: [{ to: "READY", label: "Ready (tell customer)" }],
  READY: [{ to: "HANDED_OVER", label: "Handed over" }],
};

export default function FallPicoDashboard() {
  const [tab, setTab] = useState<"board" | "workers" | "cost">("board");
  return (
    <Page title="Fall-pico" crumb="Saree finishing" actions={
      <div className="flex gap-2">{(["board", "workers", "cost"] as const).map((t) =>
        <Button key={t} variant={t === tab ? "primary" : "secondary"} onClick={() => setTab(t)}>{t === "board" ? "Job board" : t === "workers" ? "Workers & wages" : "Cost"}</Button>)}</div>}>
      {tab === "board" && <Board />}
      {tab === "workers" && <Workers />}
      {tab === "cost" && <Cost />}
    </Page>
  );
}

function Board() {
  const [q, setQ] = useState("");
  const jobs = useApi(() => apiData<Job[]>(`/fp/jobs?status=${COLUMNS.join(",")}${q ? `&q=${encodeURIComponent(q)}` : ""}`));
  const workers = useApi(() => apiData<Worker[]>("/fp/workers"));
  const act = useAction();
  const [assign, setAssign] = useState<Job | null>(null);
  const [workerId, setWorkerId] = useState("");

  async function move(job: Job, to: string) {
    await act.run(() => post(`/fp/jobs/${job.id}/status`, { status: to }));
    void jobs.reload();
  }

  return (
    <>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void jobs.reload(); }}>
        <Input placeholder="Tag, bill or order number" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
        <Button type="submit" variant="secondary">Find</Button>
      </form>
      <Alert>{act.error || jobs.error}</Alert>
      {jobs.loading && !jobs.data && <Loading />}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {COLUMNS.map((col) => {
          const list = (jobs.data ?? []).filter((j) => j.status === col);
          return (
            <section key={col} className="min-w-0 rounded-lg border border-gray-200 bg-white">
              <h2 className="flex items-center justify-between border-b border-gray-100 px-4 py-2 text-sm font-semibold">{col.replace(/_/g, " ")}<span className="text-gray-500">{list.length}</span></h2>
              <ul className="space-y-2 p-3">
                {list.length === 0 && <li className="text-xs text-gray-400">Empty</li>}
                {list.map((j) => (
                  <li key={j.id} className={`rounded-md border p-3 text-sm ${j.is_late ? "border-red-300 bg-red-50" : "border-gray-200"}`}>
                    <div className="flex items-center justify-between"><span className="font-semibold">{j.tag_code}</span>{j.is_late && <Badge tone="bad">late</Badge>}</div>
                    <p className="text-xs text-gray-600">{j.product_name} · {j.source_type} {j.source_label}</p>
                    <p className="text-xs text-gray-500">Due {formatDate(j.promised_date)}{j.worker_name ? ` · ${j.worker_name}` : ""}{j.rework_count ? ` · rework ${j.rework_count}` : ""}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {j.status === "PENDING" && <Button className="!min-h-9" onClick={() => { setAssign(j); setWorkerId(""); }}>Assign</Button>}
                      {(NEXT[j.status] ?? []).map((n) => (
                        <Button key={n.to} className="!min-h-9" variant={n.tone ?? "primary"} disabled={act.busy} onClick={() => void move(j, n.to)}>{n.label}</Button>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      <Modal open={assign !== null} title={`Assign ${assign?.tag_code}`} onClose={() => setAssign(null)}>
        <div className="space-y-3">
          <Field label="Worker" hint="Empty = the worker with the fewest open jobs">
            <Select value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
              <option value="">Auto (least busy)</option>
              {(workers.data ?? []).filter((w) => w.is_active).map((w) => <option key={w.id} value={w.id}>{w.name} · {formatINR(w.rate_paise)}/piece</option>)}
            </Select>
          </Field>
          <Button disabled={act.busy} onClick={async () => {
            await act.run(() => post(`/fp/jobs/${assign!.id}/assign`, { worker_id: workerId || null }));
            setAssign(null); void jobs.reload();
          }}>Assign</Button>
        </div>
      </Modal>
    </>
  );
}

function Workers() {
  const workers = useApi(() => apiData<Worker[]>("/fp/workers"));
  const act = useAction();
  const [form, setForm] = useState({ name: "", phone: "", rate: "" });
  const [sel, setSel] = useState<Worker | null>(null);

  return (
    <>
      <Card title="Add worker">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label="Rate per saree ₹"><Input inputMode="decimal" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} /></Field>
          <div className="flex items-end"><Button disabled={act.busy || !form.name || !rupeesToPaise(form.rate)} onClick={async () => {
            await act.run(() => post("/fp/workers", { name: form.name, phone: form.phone || null, rate_paise: rupeesToPaise(form.rate) }), "Worker added.");
            setForm({ name: "", phone: "", rate: "" }); void workers.reload(); }}>Add</Button></div>
        </div>
        <div className="mt-3"><Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert></div>
      </Card>
      <Card title="Workers">
        <Table rows={workers.data ?? []} rowKey={(w) => w.id} onRowClick={setSel} empty="No workers yet." columns={[
          { key: "n", label: "Worker", render: (w) => <div><p className="font-medium">{w.name}</p><p className="text-xs text-gray-500">{w.phone}</p></div> },
          { key: "r", label: "Rate", align: "right", render: (w) => <Money paise={w.rate_paise} /> },
          { key: "a", label: "Active", render: (w) => <Badge tone={w.is_active ? "good" : "info"}>{w.is_active ? "active" : "off"}</Badge> },
          { key: "b", label: "Shop owes", align: "right", render: (w) => <Money paise={w.balance_paise} /> },
        ]} />
      </Card>
      {sel && <WorkerModal worker={sel} onClose={() => { setSel(null); void workers.reload(); }} />}
    </>
  );
}

function WorkerModal({ worker, onClose }: { worker: Worker; onClose: () => void }) {
  const st = useApi(() => apiData<Statement>(`/fp/workers/${worker.id}/statement`), [worker.id]);
  const act = useAction();
  const [amount, setAmount] = useState("");
  const [kind, setKind] = useState("PAYMENT");
  return (
    <Modal open title={`${worker.name} · statement`} onClose={onClose} wide>
      {st.data && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Sarees done" value={st.data.jobs_done} />
            <Stat label="Earned" value={formatINR(st.data.earned_paise)} />
            <Stat label="Paid + advance" value={formatINR(st.data.paid_paise + st.data.advance_paise)} />
            <Stat label="Balance" value={formatINR(st.data.balance_paise)} tone={st.data.balance_paise > 0 ? "warn" : "good"} />
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Amount ₹"><Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
            <Field label="Type"><Select value={kind} onChange={(e) => setKind(e.target.value)}><option value="PAYMENT">Wage payment</option><option value="ADVANCE">Advance</option></Select></Field>
            <Button disabled={act.busy || !rupeesToPaise(amount)} onClick={async () => {
              await act.run(() => post(`/fp/workers/${worker.id}/payments`, { amount_paise: rupeesToPaise(amount), kind }), "Saved.");
              setAmount(""); void st.reload(); }}>Record</Button>
            <Button variant="secondary" onClick={async () => { await act.run(() => patch(`/fp/workers/${worker.id}`, { is_active: !worker.is_active })); onClose(); }}>
              {worker.is_active ? "Switch off" : "Switch on"}</Button>
          </div>
          <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
          <Table rows={[...st.data.entries].reverse()} rowKey={(e) => e.id} columns={[
            { key: "d", label: "Date", render: (e) => formatDate(e.created_at, true) },
            { key: "t", label: "Entry", render: (e) => <span><Badge tone={e.amount_paise > 0 ? "warn" : "good"}>{e.type}</Badge> <span className="text-xs text-gray-500">{e.note}</span></span> },
            { key: "a", label: "Amount", align: "right", render: (e) => <Money paise={e.amount_paise} /> },
            { key: "b", label: "Balance", align: "right", render: (e) => <Money paise={e.running_balance_paise} /> },
          ]} />
        </div>
      )}
    </Modal>
  );
}

function Cost() {
  const now = new Date();
  const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() + 1 });
  const cost = useApi(() => apiData<{ wages_paise: number; material_paise: number; total_paise: number; sarees: number; cost_per_saree_paise: number | null }>(
    `/fp/cost?year=${ym.y}&month=${ym.m}`), [ym.y, ym.m]);
  const act = useAction();
  const [mat, setMat] = useState({ description: "", amount: "" });
  return (
    <>
      <div className="flex gap-2">
        <Input type="month" value={`${ym.y}-${String(ym.m).padStart(2, "0")}`} onChange={(e) => { const [y, m] = e.target.value.split("-"); setYm({ y: Number(y), m: Number(m) }); }} className="w-44" />
      </div>
      {cost.data && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Stat label="Wages" value={formatINR(cost.data.wages_paise)} />
          <Stat label="Material" value={formatINR(cost.data.material_paise)} />
          <Stat label="Sarees finished" value={cost.data.sarees} />
          <Stat label="Cost per saree" value={cost.data.cost_per_saree_paise == null ? "—" : formatINR(cost.data.cost_per_saree_paise)} />
        </div>
      )}
      <Card title="Add material spend">
        <div className="flex flex-wrap items-end gap-2">
          <Field label="What"><Input value={mat.description} onChange={(e) => setMat({ ...mat, description: e.target.value })} placeholder="Fall cloth, thread…" /></Field>
          <Field label="Amount ₹"><Input inputMode="decimal" value={mat.amount} onChange={(e) => setMat({ ...mat, amount: e.target.value })} /></Field>
          <Button disabled={act.busy || !mat.description || !rupeesToPaise(mat.amount)} onClick={async () => {
            await act.run(() => post("/fp/materials", { description: mat.description, amount_paise: rupeesToPaise(mat.amount) }), "Saved.");
            setMat({ description: "", amount: "" }); void cost.reload(); }}>Save</Button>
        </div>
        <div className="mt-2"><Alert>{act.error}</Alert></div>
      </Card>
    </>
  );
}
