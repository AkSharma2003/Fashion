import { FormEvent, useState } from "react";
import { INDIAN_STATES, type Address, type AddressInput } from "../../lib/customer";

const EMPTY: AddressInput = { name: "", phone: "", line1: "", line2: "", landmark: "", city: "", state: "", pincode: "", kind: "HOME" };
const input = "min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2 text-base text-gray-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";
const label = "mb-1 block text-sm font-medium text-gray-700";

/** Delivery address form used in My account and at checkout. */
export default function AddressForm({ initial, onSubmit, onCancel, submitLabel = "Save address", busy, error, showDefault = true }: {
  initial?: Partial<Address>; onSubmit: (a: AddressInput) => void | Promise<void>; onCancel?: () => void;
  submitLabel?: string; busy?: boolean; error?: string; showDefault?: boolean;
}) {
  const [a, setA] = useState<AddressInput>({ ...EMPTY, ...initial, line2: initial?.line2 ?? "", landmark: initial?.landmark ?? "",
                                              is_default: initial?.is_default ?? false });
  const set = <K extends keyof AddressInput>(k: K, v: AddressInput[K]) => setA({ ...a, [k]: v });

  function submit(e: FormEvent) {
    e.preventDefault();
    void onSubmit({ ...a, name: a.name.trim(), line1: a.line1.trim(), city: a.city.trim(),
                    line2: a.line2?.trim() || null, landmark: a.landmark?.trim() || null });
  }

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
      <div><label className={label} htmlFor="addr-name">Full name</label>
        <input id="addr-name" className={input} required minLength={2} maxLength={100} autoComplete="name"
          value={a.name} onChange={(e) => set("name", e.target.value)} /></div>
      <div><label className={label} htmlFor="addr-phone">Mobile number</label>
        <input id="addr-phone" className={input} required inputMode="numeric" pattern="\d{10}" maxLength={10} autoComplete="tel"
          placeholder="10-digit mobile" value={a.phone} onChange={(e) => set("phone", e.target.value.replace(/\D/g, ""))} /></div>
      <div className="sm:col-span-2"><label className={label} htmlFor="addr-line1">Flat, house no., building</label>
        <input id="addr-line1" className={input} required minLength={3} maxLength={200} autoComplete="address-line1"
          value={a.line1} onChange={(e) => set("line1", e.target.value)} /></div>
      <div className="sm:col-span-2"><label className={label} htmlFor="addr-line2">Area, street, sector, village</label>
        <input id="addr-line2" className={input} maxLength={200} autoComplete="address-line2"
          value={a.line2 ?? ""} onChange={(e) => set("line2", e.target.value)} /></div>
      <div><label className={label} htmlFor="addr-landmark">Landmark (optional)</label>
        <input id="addr-landmark" className={input} maxLength={100} placeholder="e.g. near Apollo hospital"
          value={a.landmark ?? ""} onChange={(e) => set("landmark", e.target.value)} /></div>
      <div><label className={label} htmlFor="addr-pincode">Pincode</label>
        <input id="addr-pincode" className={input} required inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="postal-code"
          placeholder="6 digits" value={a.pincode} onChange={(e) => set("pincode", e.target.value.replace(/\D/g, ""))} /></div>
      <div><label className={label} htmlFor="addr-city">Town / city</label>
        <input id="addr-city" className={input} required minLength={2} maxLength={64} autoComplete="address-level2"
          value={a.city} onChange={(e) => set("city", e.target.value)} /></div>
      <div><label className={label} htmlFor="addr-state">State</label>
        <select id="addr-state" className={input} required value={a.state} onChange={(e) => set("state", e.target.value)}>
          <option value="">Choose a state</option>
          {INDIAN_STATES.map((s) => <option key={s}>{s}</option>)}
        </select></div>

      <fieldset className="sm:col-span-2">
        <legend className={label}>Address type</legend>
        <div className="flex gap-2">
          {(["HOME", "WORK", "OTHER"] as const).map((k) => (
            <button key={k} type="button" onClick={() => set("kind", k)} aria-pressed={a.kind === k}
              className={`min-h-10 rounded-full border px-4 text-sm font-medium ${a.kind === k ? "border-primary bg-primary/10 text-primary" : "border-gray-300 text-gray-700"}`}>
              {k === "HOME" ? "Home" : k === "WORK" ? "Work" : "Other"}
            </button>
          ))}
        </div>
      </fieldset>

      {showDefault && (
        <label className="flex items-center gap-2 text-sm text-gray-700 sm:col-span-2">
          <input type="checkbox" className="h-4 w-4 accent-primary" checked={Boolean(a.is_default)}
            onChange={(e) => set("is_default", e.target.checked)} />
          Make this my default address
        </label>
      )}

      {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2">{error}</p>}

      <div className="flex gap-3 sm:col-span-2">
        <button type="submit" disabled={busy}
          className="min-h-11 rounded-lg bg-primary px-6 font-semibold text-white hover:bg-primary-dark disabled:opacity-60">
          {busy ? "Saving…" : submitLabel}
        </button>
        {onCancel && <button type="button" onClick={onCancel} className="min-h-11 rounded-lg border border-gray-300 px-6 font-medium text-gray-700 hover:bg-gray-50">Cancel</button>}
      </div>
    </form>
  );
}
