import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Alert, Badge, Button, Field, Input, Modal } from "../../components/ui";
import { apiData, errorMessage, post } from "../../lib/api/client";
import { getAccessToken, staffHome } from "../../lib/auth/session";
import { hasRole, StaffProvider, useStaff } from "../../lib/auth/staff";
import { kvGet, kvSet } from "../../lib/offline/db";
import { useT } from "../../lib/i18n";
import { formatDate, formatINR, rupeesToPaise } from "../../lib/money";
import type { CartLine, KhataCustomer, Payment, PosItem } from "../../features/pos/types";
import { usePosSync } from "../../features/pos/usePosSync";

const COUNTER_KEY = "wearverse.pos.counter";
type CounterInfo = { code: string; name: string; shop: { id: string; code: string; name: string } };

function readCounter(): CounterInfo | null {
  try {
    const raw = localStorage.getItem(COUNTER_KEY);
    return raw ? (JSON.parse(raw) as CounterInfo) : null;
  } catch {
    return null;
  }
}

function saveCounter(c: CounterInfo | null): void {
  try {
    if (c) localStorage.setItem(COUNTER_KEY, JSON.stringify(c));
    else localStorage.removeItem(COUNTER_KEY);
  } catch {
    // storage blocked: the counter is asked again next time
  }
}

type Printed = { bill_no: string; lines: CartLine[]; payments: Payment[]; total: number; customer: KhataCustomer | null; at: string };

function PosInner({ counter, onChangeCounter }: { counter: CounterInfo; onChangeCounter: () => void }) {
  const COUNTER = counter.code;
  const { me, loading } = useStaff();
  const { t } = useT();
  const sync = usePosSync(COUNTER);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [code, setCode] = useState("");
  const [customer, setCustomer] = useState<KhataCustomer | null>(null);
  const [phone, setPhone] = useState("");
  const [payOpen, setPayOpen] = useState(false);
  const [message, setMessage] = useState<{ tone: "good" | "bad" | "warn"; text: string } | null>(null);
  const [printed, setPrinted] = useState<Printed | null>(null);
  const [held, setHeld] = useState<{ at: string; cart: CartLine[]; customer: KhataCustomer | null }[]>([]);
  const [queueOpen, setQueueOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const scanRef = useRef<HTMLInputElement>(null);

  const items = sync.snapshot?.items ?? [];
  const rules = sync.snapshot?.rules;
  const index = useMemo(() => {
    const m = new Map<string, PosItem>();
    items.forEach((i) => i.codes.forEach((c) => m.set(c.toLowerCase(), i)));
    return m;
  }, [items]);
  const gross = cart.reduce((s, l) => s + l.item.price_paise * l.qty, 0);
  const discount = cart.reduce((s, l) => s + l.discount_paise, 0);
  const total = gross - discount;
  const failed = sync.queue.filter((b) => b.status === "failed").length;

  useEffect(() => { void kvGet<typeof held>("held").then((h) => h && setHeld(h)); }, []);
  useEffect(() => {
    const keys = (e: KeyboardEvent) => {
      if (e.key === "F2") { e.preventDefault(); scanRef.current?.focus(); }
      if (e.key === "F4" && cart.length) { e.preventDefault(); setPayOpen(true); }
    };
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [cart.length]);

  if (!loading && !me && !getAccessToken()) return <Navigate to="/login?next=/pos" replace />;
  if (me && !hasRole(me, "Cashier", "Manager")) return <Navigate to={staffHome(me.role)} replace />;

  function addItem(item: PosItem) {
    const limit = rules?.fall_pico_limit_paise ?? 100000;
    setCart((c) => {
      const found = c.find((l) => l.item.variant_id === item.variant_id);
      if (found) return c.map((l) => (l === found ? { ...l, qty: l.qty + 1 } : l));
      return [...c, { item, qty: 1, discount_paise: 0, fall_pico: item.fall_pico_eligible && item.price_paise > limit }];
    });
    setMessage(item.on_hand <= 0 ? { tone: "warn", text: `${item.name}: system shows no stock. The bill is still allowed; the owner gets a stock alert.` } : null);
  }

  function onScan(e: React.FormEvent) {
    e.preventDefault();
    const c = code.trim().toLowerCase();
    if (!c) return;
    const item = index.get(c) ?? items.find((i) => i.name.toLowerCase().includes(c));
    if (item) addItem(item);
    else setMessage({ tone: "bad", text: `No item for "${code}". Check the label or search by name.` });
    setCode("");
  }

  function findCustomer() {
    const c = sync.snapshot?.khata_customers.find((k) => k.phone.endsWith(phone.trim()) && phone.trim().length >= 4);
    setCustomer(c ?? null);
    if (!c) setMessage({ tone: "warn", text: "No khata customer with this phone. Open a khata in the back office first." });
  }

  async function hold() {
    const next = [...held, { at: new Date().toISOString(), cart, customer }];
    setHeld(next);
    await kvSet("held", next);
    setCart([]); setCustomer(null); setPhone("");
  }

  async function finish(payments: Payment[], approval: { pin?: string; reason?: string }) {
    const bill_no = await sync.nextBillNo();
    const body = {
      idempotency_key: bill_no, counter_id: COUNTER, bill_no, customer_id: customer?.customer_id ?? null,
      items: cart.map((l) => ({ variant_id: l.item.variant_id, qty: l.qty, price: l.item.price_paise,
        discount_paise: l.discount_paise, fall_pico_declined: l.item.fall_pico_eligible && !l.fall_pico })),
      payments: payments.filter((p) => p.amount > 0),
      sold_by: me?.id, approval: approval.pin ? approval : null, created_at_device: new Date().toISOString(),
    };
    await sync.enqueue({ key: bill_no, body, createdAt: new Date().toISOString(), status: "queued",
      summary: { total_paise: total, customer: customer?.name, lines: cart.length } });
    setPrinted({ bill_no, lines: cart, payments, total, customer, at: new Date().toISOString() });
    setCart([]); setCustomer(null); setPhone(""); setPayOpen(false);
    setMessage({ tone: "good", text: `Bill ${bill_no} saved${sync.online ? "" : " offline. It will be sent when the internet is back"}.` });
    scanRef.current?.focus();
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#F7F7F7] text-[#111111] print:bg-white">
      <header className="flex flex-wrap items-center justify-between gap-3 bg-[#111111] px-4 py-3 text-white print:hidden">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">{sync.snapshot?.shop?.name ?? counter.shop.name}</span>
          <span className="text-sm text-gray-300">Counter {COUNTER} · {me?.full_name ?? "…"}</span>
          {sync.queue.length === 0 && (
            <button type="button" onClick={onChangeCounter} className="rounded px-2 py-0.5 text-xs text-gray-300 underline hover:text-white">Change counter</button>
          )}
          {rules?.pos_mode === "parallel" && <Badge tone="warn">parallel run: bills saved for comparison only</Badge>}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className={`rounded-full px-3 py-1 ${sync.online ? "bg-green-600" : "bg-red-600"}`}>{sync.online ? t("Online") : t("Offline")}</span>
          <button type="button" onClick={() => setQueueOpen(true)} className={`rounded-full px-3 py-1 ${failed ? "bg-red-600" : "bg-white/15"}`}>
            {t("To sync")}: {sync.queue.length}{failed ? ` (${failed} need attention)` : ""}</button>
          <span className="text-gray-400">Synced {sync.lastSync ? formatDate(sync.lastSync, true) : "never"}</span>
          <button type="button" onClick={() => void sync.syncNow()} className="rounded px-2 py-1 hover:bg-white/10">⟳</button>
          <button type="button" onClick={() => setRegisterOpen(true)} className="rounded px-2 py-1 hover:bg-white/10">{t("Cash register")}</button>
          <Link to="/backoffice/bills" className="rounded px-2 py-1 hover:bg-white/10">{t("Returns")}</Link>
          <Link to="/backoffice" className="rounded px-2 py-1 hover:bg-white/10">{t("Back office")}</Link>
        </div>
      </header>

      {!sync.snapshot && <p className="p-6 text-base">Loading items… (needs internet the very first time)</p>}

      {sync.snapshot && (
        <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_380px] print:hidden">
          <section className="min-w-0 space-y-3">
            <form onSubmit={onScan} className="flex gap-2">
              <input ref={scanRef} autoFocus value={code} onChange={(e) => setCode(e.target.value)} list="pos-items"
                placeholder={t("Scan barcode or type item name (F2)")} aria-label="Scan barcode"
                className="min-h-14 w-full rounded-md border-2 border-[#111111] bg-white px-4 text-lg outline-none" />
              <datalist id="pos-items">{items.slice(0, 500).map((i) => <option key={i.variant_id} value={i.sku}>{i.name} {i.size} {i.color}</option>)}</datalist>
              <Button big type="submit">{t("Add")}</Button>
            </form>
            {message && <Alert tone={message.tone}>{message.text}</Alert>}

            <div className="rounded-lg border border-gray-200 bg-white">
              {cart.length === 0 && <p className="p-8 text-center text-base text-gray-500">{t("Scan the first item.")}</p>}
              <ul className="divide-y divide-gray-100">
                {cart.map((l, i) => (
                  <li key={l.item.variant_id} className="flex flex-wrap items-center gap-3 p-3 text-base">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{l.item.name}</p>
                      <p className="text-sm text-gray-500">{l.item.sku} {[l.item.size, l.item.color].filter(Boolean).join(" / ")} · {formatINR(l.item.price_paise)}</p>
                      {l.item.fall_pico_eligible && l.item.price_paise > (rules?.fall_pico_limit_paise ?? 0) && (
                        <label className="mt-1 flex items-center gap-2 text-sm">
                          <input type="checkbox" className="h-5 w-5" checked={l.fall_pico} onChange={(e) => setCart(cart.map((x, j) => j === i ? { ...x, fall_pico: e.target.checked } : x))} />
                          Fall-pico (free) — customer wants it</label>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button variant="secondary" className="!min-h-12 w-12" onClick={() => setCart(cart.flatMap((x, j) => j !== i ? [x] : x.qty > 1 ? [{ ...x, qty: x.qty - 1 }] : []))}>−</Button>
                      <span className="w-8 text-center font-semibold">{l.qty}</span>
                      <Button variant="secondary" className="!min-h-12 w-12" onClick={() => setCart(cart.map((x, j) => j === i ? { ...x, qty: x.qty + 1 } : x))}>+</Button>
                    </div>
                    <input aria-label="Discount ₹" inputMode="decimal" placeholder="Disc ₹" defaultValue={l.discount_paise ? l.discount_paise / 100 : ""}
                      onBlur={(e) => { const p = e.target.value ? rupeesToPaise(e.target.value) : 0; if (!Number.isNaN(p)) setCart(cart.map((x, j) => j === i ? { ...x, discount_paise: Math.min(p, x.item.price_paise * x.qty) } : x)); }}
                      className="min-h-12 w-24 rounded-md border border-gray-300 px-2 text-right" />
                    <span className="w-28 text-right font-semibold tabular-nums">{formatINR(l.item.price_paise * l.qty - l.discount_paise)}</span>
                  </li>
                ))}
              </ul>
            </div>
            {held.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {held.map((h, i) => (
                  <Button key={h.at} variant="secondary" onClick={async () => {
                    setCart(h.cart); setCustomer(h.customer); const next = held.filter((_, j) => j !== i); setHeld(next); await kvSet("held", next);
                  }}>Resume held bill {i + 1} ({h.cart.length} items)</Button>
                ))}
              </div>
            )}
          </section>

          <aside className="space-y-3">
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="mb-2 font-medium">{t("Khata customer (optional)")}</p>
              {customer ? (
                <div className="space-y-1 text-base">
                  <p className="font-semibold">{customer.name} · {customer.phone}</p>
                  <p>Balance {formatINR(customer.balance_paise)} · Limit {formatINR(customer.credit_limit_paise)}</p>
                  {!sync.online && <p className="text-sm text-[#8A5A00]">Offline: balance may be outdated.</p>}
                  <Button variant="secondary" onClick={() => { setCustomer(null); setPhone(""); }}>{t("Remove")}</Button>
                </div>
              ) : (
                <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); findCustomer(); }}>
                  <Input inputMode="tel" placeholder={t("Phone number")} value={phone} onChange={(e) => setPhone(e.target.value)} />
                  <Button type="submit" variant="secondary">{t("Find")}</Button>
                </form>
              )}
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-base">
              <div className="flex justify-between"><span>{t("Items")}</span><span>{cart.reduce((s, l) => s + l.qty, 0)}</span></div>
              {discount > 0 && <div className="flex justify-between text-[#1E8E3E]"><span>{t("Discount")}</span><span>−{formatINR(discount)}</span></div>}
              <div className="mt-2 flex justify-between text-2xl font-semibold"><span>{t("Total")}</span><span className="tabular-nums">{formatINR(total)}</span></div>
              <p className="mt-1 text-xs text-gray-500">Prices include GST. Final GST is worked out by the server.</p>
            </div>
            <Button big className="w-full text-lg" disabled={!cart.length} onClick={() => setPayOpen(true)}>{t("Take payment (F4)")}</Button>
            <div className="grid grid-cols-2 gap-2">
              <Button big variant="secondary" disabled={!cart.length} onClick={() => void hold()}>{t("Hold bill")}</Button>
              <Button big variant="secondary" disabled={!cart.length} onClick={() => { if (window.confirm("Clear this bill?")) { setCart([]); setCustomer(null); } }}>{t("Clear")}</Button>
            </div>
            {printed && <Button big variant="secondary" className="w-full" onClick={() => window.print()}>Print last bill ({printed.bill_no})</Button>}
          </aside>
        </div>
      )}

      {payOpen && (
        <PaymentModal total={total} gross={gross} discount={discount} customer={customer} role={me?.role ?? ""}
          limits={rules?.discount_limit_percent ?? {}} queue={sync.queue} onClose={() => setPayOpen(false)} onDone={finish} />
      )}
      <QueueModal open={queueOpen} onClose={() => setQueueOpen(false)} sync={sync} />
      <RegisterModal open={registerOpen} onClose={() => setRegisterOpen(false)} pending={sync.queue.length} counter={COUNTER} />
      {printed && <Receipt bill={printed} shop={sync.snapshot?.shop?.name ?? rules?.shop_name ?? counter.shop.name}
        gstin={sync.snapshot?.shop?.gstin ?? rules?.shop_gstin ?? ""} address={sync.snapshot?.shop?.address ?? ""}
        phone={sync.snapshot?.shop?.phone ?? ""} />}
    </div>
  );
}

function PaymentModal({ total, gross, discount, customer, role, limits, queue, onClose, onDone }: {
  total: number; gross: number; discount: number; customer: KhataCustomer | null; role: string; limits: Record<string, number>;
  queue: { body: Record<string, unknown>; status: string }[]; onClose: () => void;
  onDone: (p: Payment[], approval: { pin?: string; reason?: string }) => Promise<void>;
}) {
  const [amounts, setAmounts] = useState<Record<Payment["mode"], string>>({ CASH: (total / 100).toString(), UPI: "", CARD: "", KHATA: "" });
  const [pin, setPin] = useState("");
  const [reason, setReason] = useState("");
  const [cashGiven, setCashGiven] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const paise = (m: Payment["mode"]) => (amounts[m] ? rupeesToPaise(amounts[m]) : 0);
  const paid = (["CASH", "UPI", "CARD", "KHATA"] as const).reduce((s, m) => s + (paise(m) || 0), 0);
  const khata = paise("KHATA") || 0;
  // Offline credit check: cached balance + khata bills still waiting in the queue for this customer.
  const pendingKhata = customer ? queue.filter((b) => b.body.customer_id === customer.customer_id)
    .reduce((s, b) => s + ((b.body.payments as Payment[]) ?? []).filter((p) => p.mode === "KHATA").reduce((a, p) => a + p.amount, 0), 0) : 0;
  const overBy = customer ? Math.max(customer.balance_paise + pendingKhata + khata - customer.credit_limit_paise, 0) : 0;
  const discountPct = gross ? (discount * 100) / gross : 0;
  const needsPin = overBy > 0 || discountPct > (limits[role] ?? 0) && !["Owner", "Admin"].includes(role);
  const change = cashGiven ? rupeesToPaise(cashGiven) - (paise("CASH") || 0) : 0;

  function only(mode: Payment["mode"]) {
    setAmounts({ CASH: "", UPI: "", CARD: "", KHATA: "", [mode]: (total / 100).toString() });
  }

  async function confirm() {
    if (paid !== total) return setError(`Payments add up to ${formatINR(paid)}; the bill is ${formatINR(total)}.`);
    if (khata && !customer) return setError("Choose the khata customer first.");
    if (needsPin && !pin) return setError("Manager PIN is needed for this bill.");
    if (overBy && !reason.trim()) return setError("Give a reason for allowing credit over the limit.");
    setSaving(true);
    try {
      await onDone((["CASH", "UPI", "CARD", "KHATA"] as const).map((mode) => ({ mode, amount: paise(mode) || 0 })), { pin: pin || undefined, reason: reason || undefined });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={`Payment · ${formatINR(total)}`} onClose={onClose}>
      <div className="space-y-3 text-base">
        <div className="grid grid-cols-4 gap-2">
          {(["CASH", "UPI", "CARD", "KHATA"] as const).map((m) => (
            <Button key={m} big variant="secondary" disabled={m === "KHATA" && !customer} onClick={() => only(m)}>{m === "KHATA" ? "Khata" : m[0] + m.slice(1).toLowerCase()}</Button>
          ))}
        </div>
        <p className="text-sm text-gray-500">For a split payment, type each part below.</p>
        <div className="grid grid-cols-2 gap-2">
          {(["CASH", "UPI", "CARD", "KHATA"] as const).map((m) => (
            <Field key={m} label={m === "KHATA" ? "Khata (udhar)" : m}>
              <Input inputMode="decimal" disabled={m === "KHATA" && !customer} value={amounts[m]} onChange={(e) => setAmounts({ ...amounts, [m]: e.target.value })} />
            </Field>
          ))}
        </div>
        {paise("CASH") > 0 && (
          <Field label="Cash given by customer (for change)">
            <Input inputMode="decimal" value={cashGiven} onChange={(e) => setCashGiven(e.target.value)} />
          </Field>
        )}
        {change > 0 && <p className="text-lg font-semibold">Give back {formatINR(change)}</p>}
        {overBy > 0 && <Alert tone="warn">Khata limit crossed by {formatINR(overBy)}. Only a manager or owner can allow it, with a reason.</Alert>}
        {needsPin && (
          <div className="grid grid-cols-2 gap-2">
            <Field label="Manager PIN"><Input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} /></Field>
            {overBy > 0 && <Field label="Reason"><Input value={reason} onChange={(e) => setReason(e.target.value)} /></Field>}
          </div>
        )}
        <Alert>{error}</Alert>
        <Button big className="w-full text-lg" disabled={saving} onClick={() => void confirm()}>Done · save bill</Button>
      </div>
    </Modal>
  );
}

function QueueModal({ open, onClose, sync }: { open: boolean; onClose: () => void; sync: ReturnType<typeof usePosSync> }) {
  const [pins, setPins] = useState<Record<string, string>>({});
  return (
    <Modal open={open} title="Bills waiting to sync" onClose={onClose}>
      {sync.queue.length === 0 ? <p className="text-sm text-gray-500">All bills are synced.</p> : (
        <ul className="space-y-3">
          {sync.queue.map((b) => (
            <li key={b.key} className="rounded-md border border-gray-200 p-3 text-sm">
              <div className="flex justify-between"><b>{b.key}</b><span>{formatINR(b.summary.total_paise)}</span></div>
              <p className="text-xs text-gray-500">{formatDate(b.createdAt, true)} {b.summary.customer ?? ""}</p>
              {b.status === "failed" ? (
                <div className="mt-2 space-y-2">
                  <Alert>{b.error}</Alert>
                  {(b.code === "CREDIT_LIMIT_EXCEEDED" || b.code?.startsWith("APPROVAL")) && (
                    <Input placeholder="Manager PIN" type="password" value={pins[b.key] ?? ""} onChange={(e) => setPins({ ...pins, [b.key]: e.target.value })} />
                  )}
                  <div className="flex gap-2">
                    <Button onClick={() => void sync.retry(b, pins[b.key] ? { approval: { pin: pins[b.key], reason: "Approved at counter after sync" } } : undefined)}>Retry</Button>
                    <Button variant="danger" onClick={() => { if (window.confirm("Remove this bill? Only do this if it was billed again another way.")) void sync.discard(b); }}>Remove</Button>
                  </div>
                </div>
              ) : <Badge>queued</Badge>}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

function RegisterModal({ open, onClose, pending, counter: COUNTER }: { open: boolean; onClose: () => void; pending: number; counter: string }) {
  const [current, setCurrent] = useState<{ id: string; opening_cash_paise: number; expected_cash_paise: number; bills: number; by_mode: Record<string, number> } | null>(null);
  const [amount, setAmount] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => {
    if (open) void apiData<typeof current>(`/pos/registers/current?counter_id=${COUNTER}`).then(setCurrent).catch((e) => setMsg(errorMessage(e)));
  }, [open]);
  return (
    <Modal open={open} title="Cash register" onClose={onClose}>
      <div className="space-y-3 text-base">
        {current ? (
          <>
            <p>Open since start of shift · {current.bills} bills · expected cash <b>{formatINR(current.expected_cash_paise)}</b></p>
            {pending > 0 && <Alert tone="warn">{pending} bill(s) are not synced yet. Sync them before closing the day.</Alert>}
            <Field label="Counted cash ₹"><Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
            <Button big className="w-full" onClick={async () => {
              try {
                const r = await post<{ difference_paise: number }>("/pos/registers/close", { counter_id: COUNTER, counted_cash_paise: rupeesToPaise(amount), pending_offline_bills: pending });
                setMsg(`Day closed. Difference ${formatINR(r.difference_paise)}.`); setCurrent(null);
              } catch (e) { setMsg(errorMessage(e)); }
            }}>Close day</Button>
          </>
        ) : (
          <>
            <Field label="Opening cash ₹"><Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
            <Button big className="w-full" onClick={async () => {
              try { await post("/pos/registers/open", { counter_id: COUNTER, opening_cash_paise: rupeesToPaise(amount || "0") }); setMsg("Register opened."); onClose(); }
              catch (e) { setMsg(errorMessage(e)); }
            }}>Open register</Button>
          </>
        )}
        <Alert tone="warn">{msg}</Alert>
      </div>
    </Modal>
  );
}

function Receipt({ bill, shop, gstin, address, phone }: { bill: Printed; shop: string; gstin: string; address: string; phone: string }) {
  return (
    <div className="hidden p-2 font-mono text-[12px] print:block">
      <p className="text-center text-base font-bold">{shop}</p>
      {address && <p className="text-center">{address}</p>}
      {phone && <p className="text-center">Ph {phone}</p>}
      {gstin && <p className="text-center">GSTIN {gstin}</p>}
      <p>Bill {bill.bill_no} · {formatDate(bill.at, true)}</p>
      {bill.customer && <p>Customer: {bill.customer.name}</p>}
      <hr className="my-1 border-dashed border-black" />
      {bill.lines.map((l) => (
        <div key={l.item.variant_id} className="flex justify-between"><span>{l.qty} x {l.item.name}</span><span>{formatINR(l.item.price_paise * l.qty - l.discount_paise)}</span></div>
      ))}
      <hr className="my-1 border-dashed border-black" />
      <div className="flex justify-between font-bold"><span>TOTAL (incl. GST)</span><span>{formatINR(bill.total)}</span></div>
      {bill.payments.filter((p) => p.amount > 0).map((p) => <div key={p.mode} className="flex justify-between"><span>{p.mode}</span><span>{formatINR(p.amount)}</span></div>)}
      <p className="mt-2 text-center">Thank you! Visit again.</p>
    </div>
  );
}

/** Each device bills on one counter, and each counter belongs to one shop. Asked once, then remembered. */
function CounterGate() {
  const { me, loading } = useStaff();
  const [counter, setCounter] = useState<CounterInfo | null>(readCounter);
  const [choices, setChoices] = useState<CounterInfo[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!me) return;
    apiData<CounterInfo[]>("/pos/counters").then((list) => {
      setChoices(list);
      setCounter((current) => {
        const still = current && list.find((c) => c.code === current.code);
        const pick = still ?? (list.length === 1 ? list[0] : null);
        saveCounter(pick ?? null);
        return pick ?? null;
      });
    }).catch((e) => setError(errorMessage(e)));   // offline: keep the counter saved on this device
  }, [me]);

  if (!loading && !me && !getAccessToken()) return <Navigate to="/login?next=/pos" replace />;
  if (counter) return <PosInner counter={counter} onChangeCounter={() => { saveCounter(null); setCounter(null); }} />;
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F7F7F7] p-4 text-[#111111]">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6">
        <h1 className="text-xl font-semibold">Which counter is this?</h1>
        <p className="mt-1 text-sm text-gray-600">Bills from this device go to the shop of the counter you pick. You choose it once.</p>
        {error && <p className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {!choices && !error && <p className="mt-4 text-sm text-gray-500">Loading counters…</p>}
        <div className="mt-4 space-y-2">
          {(choices ?? []).map((c) => (
            <button key={c.code} type="button" onClick={() => { saveCounter(c); setCounter(c); }}
              className="flex w-full items-center justify-between rounded-lg border border-gray-300 px-4 py-3 text-left hover:border-[#111111] hover:bg-gray-50">
              <span><span className="block font-semibold">{c.shop.name}</span><span className="text-sm text-gray-500">{c.name}</span></span>
              <span className="font-mono text-sm">{c.code}</span>
            </button>
          ))}
          {choices && choices.length === 0 && <p className="text-sm text-gray-600">No counter is set up for your shop. Ask the owner to add one.</p>}
        </div>
      </div>
    </div>
  );
}

export default function PosScreen() {
  return (
    <StaffProvider>
      <CounterGate />
    </StaffProvider>
  );
}
