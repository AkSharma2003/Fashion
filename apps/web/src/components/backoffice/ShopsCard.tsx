import { useState } from "react";
import { Alert, Button, Card, Field, Input } from "../ui";
import { apiData, patch } from "../../lib/api/client";
import { useAction, useApi } from "../../lib/hooks/useApi";
import type { Shop } from "../../lib/shops";

/** Settings → Shops: each shop's own business details (they go on its bills and to its Tally company). */
export default function ShopsCard() {
  const shops = useApi(() => apiData<Shop[]>("/shops"));
  const act = useAction();
  const [draft, setDraft] = useState<Record<string, Partial<Shop>>>({});
  const val = (s: Shop, k: keyof Shop) => String(draft[s.id]?.[k] ?? s[k] ?? "");
  const set = (s: Shop, k: keyof Shop, v: string) => setDraft({ ...draft, [s.id]: { ...draft[s.id], [k]: v } });

  async function save(s: Shop) {
    const d = draft[s.id] ?? {};
    const body: Record<string, string> = {};
    for (const k of ["name", "gstin", "state_code", "address", "phone", "tally_company"] as const) {
      if (d[k] !== undefined) body[k] = String(d[k]).trim();
    }
    if (body.gstin) body.gstin = body.gstin.toUpperCase();
    if (!Object.keys(body).length) return act.setNotice("Nothing to save.");
    const r = await act.run(() => patch(`/shops/${s.id}`, body), `${body.name ?? s.name} saved.`);
    if (r) { setDraft({ ...draft, [s.id]: {} }); void shops.reload(); }
  }

  return (
    <Card title="Shops">
      <p className="mb-4 text-sm text-gray-600">Each shop is its own GST business: its name, GSTIN and address print on its bills,
        and its sales go to its own Tally company.</p>
      <Alert>{act.error || shops.error}</Alert>
      <Alert tone="good">{act.notice}</Alert>
      <div className="grid gap-4 xl:grid-cols-3">
        {(shops.data ?? []).map((s) => (
          <div key={s.id} className="rounded-lg border border-gray-200 p-4">
            <p className="mb-3 flex items-center justify-between text-sm text-gray-500">
              <span>Code <span className="font-mono font-semibold text-[#111111]">{s.code}</span></span>
              {s.is_main && <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">website / main</span>}
            </p>
            <div className="space-y-3">
              <Field label="Shop name"><Input value={val(s, "name")} onChange={(e) => set(s, "name", e.target.value)} /></Field>
              <Field label="GSTIN" hint="15 characters, e.g. 24ABCDE1234F1Z5"><Input maxLength={15} value={val(s, "gstin")}
                onChange={(e) => set(s, "gstin", e.target.value.toUpperCase())} /></Field>
              <Field label="State code" hint="First 2 digits of the GSTIN (Gujarat = 24)"><Input inputMode="numeric" maxLength={2}
                value={val(s, "state_code")} onChange={(e) => set(s, "state_code", e.target.value.replace(/\D/g, ""))} /></Field>
              <Field label="Address (printed on bills)"><Input maxLength={300} value={val(s, "address")} onChange={(e) => set(s, "address", e.target.value)} /></Field>
              <Field label="Phone"><Input inputMode="numeric" maxLength={10} value={val(s, "phone")}
                onChange={(e) => set(s, "phone", e.target.value.replace(/\D/g, ""))} /></Field>
              <Field label="Tally company name" hint="Exactly as in TallyPrime"><Input maxLength={100} value={val(s, "tally_company")}
                onChange={(e) => set(s, "tally_company", e.target.value)} /></Field>
              <Button disabled={act.busy} onClick={() => void save(s)}>Save {s.code}</Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
