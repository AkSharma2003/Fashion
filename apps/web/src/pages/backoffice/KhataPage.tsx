import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Select, Stat, Table } from "../../components/ui";
import { apiData, patch, post } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";

type Account = {
  id: string; customer_id: string; customer_name: string; phone_number: string; is_active: boolean;
  balance_paise: number; credit_limit_paise: number; credit_days: number; is_disputed: boolean;
  reminders_paused: boolean; overdue_paise: number; tally_ledger_name: string | null;
  ageing: Record<string, number>;
};
type Entry = { id: string; seq: number; type: string; amount_paise: number; running_balance_paise: number;
  ref_label: string | null; payment_mode: string | null; note: string | null; reverses_entry_id: string | null; created_at: string };
type Message = { id: string; purpose: string; status: string; channel: string | null; text: string | null; flagged: boolean; created_at: string };
type LedgerData = { account: Account; entries: Entry[]; messages: Message[] };

export default function KhataPage() {
  const { me } = useStaff();
  const [q, setQ] = useState("");
  const [onlyDue, setOnlyDue] = useState(false);
  const list = useApi(() => apiData<{ total_outstanding_paise: number; accounts: Account[] }>(
    `/khata/accounts?only_due=${onlyDue}${q ? `&q=${encodeURIComponent(q)}` : ""}`), [onlyDue]);
  // "?account=<id>" (e.g. from the Users page) opens that customer's khata straight away.
  const [params, setParams] = useSearchParams();
  const [openId, setOpenId] = useState<string | null>(params.get("account"));
  const [newOpen, setNewOpen] = useState(false);

  return (
    <Page title="Customer khata" crumb="Khata"
      actions={hasRole(me, "Manager") && <Button onClick={() => setNewOpen(true)}>Open khata</Button>}>
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Total outstanding" value={formatINR(list.data?.total_outstanding_paise)} tone="warn" />
        <Stat label="Customers with dues" value={list.data?.accounts.filter((a) => a.balance_paise > 0).length ?? "—"} />
        <Stat label="Overdue" value={formatINR(list.data?.accounts.reduce((s, a) => s + a.overdue_paise, 0))} tone="bad" />
      </div>
      <Card title="Accounts" actions={
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void list.reload(); }}>
          <Input placeholder="Name or phone" value={q} onChange={(e) => setQ(e.target.value)} className="w-48" />
          <Button type="submit" variant="secondary">Search</Button>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={onlyDue} onChange={(e) => setOnlyDue(e.target.checked)} /> Only dues</label>
        </form>}>
        {list.loading && !list.data && <Loading />}
        <Alert>{list.error}</Alert>
        {list.data && (
          <Table rows={list.data.accounts} rowKey={(a) => a.id} onRowClick={(a) => setOpenId(a.id)} empty="No khata accounts yet." columns={[
            { key: "name", label: "Customer", render: (a) => <div><p className="font-medium">{a.customer_name}</p><p className="text-xs text-gray-500">{a.phone_number}</p></div> },
            { key: "status", label: "", render: (a) => <div className="flex gap-1">{!a.is_active && <Badge tone="info">inactive</Badge>}{a.is_disputed && <Badge tone="bad">dispute</Badge>}{a.overdue_paise > 0 && <Badge tone="bad">overdue</Badge>}</div> },
            { key: "limit", label: "Limit", align: "right", render: (a) => <Money paise={a.credit_limit_paise} /> },
            { key: "bal", label: "Balance", align: "right", render: (a) => <span className="font-semibold"><Money paise={a.balance_paise} signed /></span> },
          ]} />
        )}
      </Card>
      {openId && <LedgerModal accountId={openId} onClose={() => { setOpenId(null); if (params.get("account")) setParams({}); void list.reload(); }} />}
      <NewAccountModal open={newOpen} onClose={() => setNewOpen(false)} onSaved={() => { setNewOpen(false); void list.reload(); }} />
    </Page>
  );
}

function LedgerModal({ accountId, onClose }: { accountId: string; onClose: () => void }) {
  const { me } = useStaff();
  const ledger = useApi(() => apiData<LedgerData>(`/khata/accounts/${accountId}/ledger`), [accountId]);
  const act = useAction();
  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState("CASH");
  const [link, setLink] = useState("");
  const [adjust, setAdjust] = useState<{ kind: string; entry_id?: string } | null>(null);
  const [reason, setReason] = useState("");
  const [adjAmount, setAdjAmount] = useState("");
  const a = ledger.data?.account;

  async function receive() {
    const paise = rupeesToPaise(amount);
    if (!paise || Number.isNaN(paise)) return act.setError("Enter a valid amount.");
    await act.run(() => post(`/khata/accounts/${accountId}/payments`, {
      amount_paise: paise, mode, idempotency_key: crypto.randomUUID() }), "Payment saved. Receipt goes on WhatsApp and Tally.");
    setAmount("");
    void ledger.reload();
  }

  async function doAdjust() {
    if (!adjust) return;
    const body: Record<string, unknown> = { kind: adjust.kind, reason };
    if (adjust.entry_id) body.entry_id = adjust.entry_id;
    if (adjust.kind !== "REVERSAL" && adjAmount) body.amount_paise = Math.round(Number(adjAmount) * 100);
    const ok = await act.run(() => post(`/khata/accounts/${accountId}/adjustments`, body), "Correction entry added.");
    if (ok) { setAdjust(null); setReason(""); setAdjAmount(""); void ledger.reload(); }
  }

  return (
    <Modal open title={a ? `${a.customer_name} · ${a.phone_number}` : "Khata"} onClose={onClose} wide>
      {ledger.loading && !ledger.data && <Loading />}
      <Alert>{ledger.error}</Alert>
      {a && ledger.data && (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Balance" value={<Money paise={a.balance_paise} signed />} />
            <Stat label="Limit" value={formatINR(a.credit_limit_paise)} note={`${a.credit_days} credit days`} />
            <Stat label="Overdue" value={formatINR(a.overdue_paise)} tone={a.overdue_paise ? "bad" : undefined} />
            <Stat label="90+ days" value={formatINR(a.ageing["90_plus"])} />
          </div>
          <Alert tone="good">{act.notice}</Alert>
          <Alert>{act.error}</Alert>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 rounded-md border border-gray-200 p-4">
              <p className="font-medium">Receive payment in shop</p>
              <div className="flex gap-2">
                <Input inputMode="decimal" placeholder="₹ amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
                <Select value={mode} onChange={(e) => setMode(e.target.value)} className="w-28">
                  <option>CASH</option><option>UPI</option><option>CARD</option><option>BANK</option>
                </Select>
              </div>
              <Button disabled={act.busy} onClick={() => void receive()} className="w-full">Save payment</Button>
            </div>
            <div className="space-y-2 rounded-md border border-gray-200 p-4">
              <p className="font-medium">Pay from home</p>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" disabled={act.busy} onClick={async () => {
                  const r = await act.run(() => post<{ url: string }>(`/khata/accounts/${accountId}/paylink`));
                  if (r) setLink(r.url);
                }}>Make Pay Now link</Button>
                <Button variant="secondary" disabled={act.busy || a.balance_paise <= 0} onClick={() =>
                  void act.run(() => post(`/khata/accounts/${accountId}/paylink?send_whatsapp=true`), "Reminder queued on WhatsApp.")}>
                  Send reminder</Button>
              </div>
              {link && <p className="break-all text-xs"><a className="underline" href={link} target="_blank" rel="noreferrer">{link}</a></p>}
              {hasRole(me, "Manager") && (
                <label className="flex items-center gap-2 pt-1 text-sm">
                  <input type="checkbox" checked={a.is_disputed} onChange={async (e) => {
                    await act.run(() => patch(`/khata/accounts/${accountId}`, { is_disputed: e.target.checked }));
                    void ledger.reload();
                  }} /> Dispute open (reminders stop)
                </label>
              )}
            </div>
          </div>

          <Card title="Ledger" actions={hasRole(me) && (
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setAdjust({ kind: "ADJUSTMENT" })}>Adjustment</Button>
              <Button variant="secondary" onClick={() => setAdjust({ kind: "WRITE_OFF" })}>Write off</Button>
            </div>)}>
            <Table rows={ledger.data.entries} rowKey={(e) => e.id} empty="No entries yet." columns={[
              { key: "d", label: "Date", render: (e) => formatDate(e.created_at, true) },
              { key: "t", label: "Entry", render: (e) => <div><Badge tone={e.amount_paise > 0 ? "warn" : "good"}>{e.type}</Badge>
                <p className="mt-1 text-xs text-gray-500">{[e.ref_label, e.payment_mode, e.note].filter(Boolean).join(" · ")}</p></div> },
              { key: "a", label: "Amount", align: "right", render: (e) => <Money paise={e.amount_paise} signed /> },
              { key: "b", label: "Balance", align: "right", render: (e) => <Money paise={e.running_balance_paise} /> },
              { key: "x", label: "", render: (e) => hasRole(me) && e.type !== "REVERSAL" && !ledger.data!.entries.some((o) => o.reverses_entry_id === e.id)
                ? <button type="button" className="text-xs underline" onClick={() => setAdjust({ kind: "REVERSAL", entry_id: e.id })}>Reverse</button> : null },
            ]} />
          </Card>

          <Card title="WhatsApp messages">
            <Table rows={ledger.data.messages} rowKey={(m) => m.id} empty="No messages yet." columns={[
              { key: "p", label: "Message", render: (m) => <div><p className="text-xs text-gray-500">{m.purpose.replace(/_/g, " ")} · {formatDate(m.created_at, true)}</p><p className="mt-1 max-w-md text-sm">{m.text ?? "—"}</p></div> },
              { key: "s", label: "Status", render: (m) => <div className="flex gap-1"><Badge>{m.status}</Badge>{m.flagged && <Badge tone="bad">check</Badge>}</div> },
              { key: "r", label: "", render: (m) => <button type="button" className="text-xs underline" onClick={async () => {
                await act.run(() => post(`/messages/${m.id}/resend`), "Message sent again."); void ledger.reload(); }}>Resend</button> },
            ]} />
          </Card>

          <Modal open={adjust !== null} title={adjust?.kind === "REVERSAL" ? "Reverse entry" : adjust?.kind === "WRITE_OFF" ? "Write off" : "Adjustment"} onClose={() => setAdjust(null)}>
            <div className="space-y-3">
              <p className="text-sm text-gray-600">Entries are never edited or deleted. This adds a correction entry; both stay visible.</p>
              {adjust?.kind !== "REVERSAL" && (
                <Field label={adjust?.kind === "WRITE_OFF" ? "Amount to write off (₹, empty = full balance)" : "Amount ₹ (+ owes more, − owes less)"}>
                  <Input inputMode="decimal" value={adjAmount} onChange={(e) => setAdjAmount(e.target.value)} />
                </Field>
              )}
              <Field label="Reason (required)"><Input value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
              <Button disabled={act.busy || reason.trim().length < 3} onClick={() => void doAdjust()}>Save</Button>
            </div>
          </Modal>
        </div>
      )}
    </Modal>
  );
}

function NewAccountModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const act = useAction();
  const [form, setForm] = useState({ full_name: "", phone_number: "", limit: "10000", days: "30", opening: "0", language: "hinglish", optin: true });
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    const ok = await act.run(() => post("/khata/accounts", {
      full_name: form.full_name, phone_number: form.phone_number,
      credit_limit_paise: rupeesToPaise(form.limit), credit_days: Number(form.days),
      opening_balance_paise: rupeesToPaise(form.opening || "0") || 0,
      whatsapp_optin: form.optin, language: form.language,
    }));
    if (ok) onSaved();
  }

  return (
    <Modal open={open} title="Open a khata" onClose={onClose}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Customer name"><Input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} /></Field>
        <Field label="Phone"><Input inputMode="tel" value={form.phone_number} onChange={(e) => set("phone_number", e.target.value)} /></Field>
        <Field label="Credit limit ₹"><Input inputMode="decimal" value={form.limit} onChange={(e) => set("limit", e.target.value)} /></Field>
        <Field label="Credit days"><Input inputMode="numeric" value={form.days} onChange={(e) => set("days", e.target.value)} /></Field>
        <Field label="Opening balance ₹" hint="Owner signs off old balances"><Input inputMode="decimal" value={form.opening} onChange={(e) => set("opening", e.target.value)} /></Field>
        <Field label="Message language">
          <Select value={form.language} onChange={(e) => set("language", e.target.value)}>
            <option value="hinglish">Hinglish</option><option value="hindi">Hindi</option><option value="english">English</option>
          </Select>
        </Field>
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={form.optin} onChange={(e) => set("optin", e.target.checked)} />
        Customer agreed to get bills on WhatsApp</label>
      <div className="mt-4 space-y-2"><Alert>{act.error}</Alert>
        <Button disabled={act.busy} onClick={() => void save()}>Open khata</Button></div>
    </Modal>
  );
}
