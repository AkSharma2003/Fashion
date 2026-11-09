import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

/** Small shared kit for back-office, POS and simple pages (SRS 9.3 design rules). */

export function Page({ title, crumb, actions, children }: { title: string; crumb?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <main className="min-w-0 p-4 text-[#111111] md:p-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          {crumb && <p className="text-xs text-gray-500">{crumb}</p>}
          <h1 className="mt-1 text-2xl font-semibold md:text-3xl">{title}</h1>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </header>
      <div className="space-y-6">{children}</div>
    </main>
  );
}

export function Card({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 rounded-lg border border-gray-200 bg-white ${className}`}>
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-5 py-3">
          {title && <h2 className="font-semibold">{title}</h2>}
          {actions}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({ label, value, note, tone }: { label: string; value: ReactNode; note?: string; tone?: "good" | "warn" | "bad" }) {
  const color = tone === "bad" ? "text-[#D93025]" : tone === "warn" ? "text-[#B06F00]" : tone === "good" ? "text-[#1E8E3E]" : "";
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      {note && <p className="mt-1 text-xs text-gray-500">{note}</p>}
    </div>
  );
}

type Variant = "primary" | "secondary" | "danger" | "ghost";

export function Button({ variant = "primary", className = "", big, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; big?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: "bg-[#111111] text-white hover:bg-black",
    secondary: "border border-gray-300 bg-white text-[#111111] hover:bg-gray-50",
    danger: "bg-[#D93025] text-white hover:bg-red-700",
    ghost: "text-[#111111] hover:bg-gray-100",
  };
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${big ? "min-h-14 text-base" : "min-h-11"} ${styles[variant]} ${className}`}
    />
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-gray-500">{hint}</span>}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`min-h-11 w-full rounded-md border border-gray-300 bg-white px-3 text-base outline-none focus:border-[#111111] focus:ring-2 focus:ring-black/10 ${props.className ?? ""}`}
    />
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`min-h-11 w-full rounded-md border border-gray-300 bg-white px-3 text-base outline-none focus:border-[#111111] ${props.className ?? ""}`}
    />
  );
}

const BADGE: Record<string, string> = {
  good: "bg-green-50 text-[#1E8E3E] ring-green-200",
  warn: "bg-amber-50 text-[#8A5A00] ring-amber-200",
  bad: "bg-red-50 text-[#D93025] ring-red-200",
  info: "bg-gray-100 text-gray-700 ring-gray-200",
};

const STATUS_TONE: Record<string, keyof typeof BADGE> = {
  // done
  done: "good", sent: "good", delivered: "good", read: "good", matched: "good", paid: "good", captured: "good",
  qc_passed: "good", ready: "good", handed_over: "good", completed: "good", approved: "good", resolved: "good",
  ready_to_pack: "good", packed: "good", shipped: "good", processed: "good", open: "warn",
  // waiting
  pending: "warn", queued: "warn", draft: "warn", assigned: "warn", in_progress: "warn", rework: "warn",
  pending_payment: "warn", fall_pico_in_progress: "warn", waiting_for_tally: "warn", sms_sent: "warn",
  confirmed: "warn", estimate: "warn", partly_returned: "warn",
  // problems
  error: "bad", failed: "bad", differences: "bad", cancelled: "bad", issue: "bad", overdue: "bad", returned: "bad",
};

export function Badge({ children, tone }: { children: ReactNode; tone?: keyof typeof BADGE }) {
  const key = tone ?? STATUS_TONE[String(children).toLowerCase()] ?? "info";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${BADGE[key]}`}>
      {String(children).replace(/_/g, " ")}
    </span>
  );
}

export function Alert({ tone = "bad", children }: { tone?: "good" | "warn" | "bad"; children: ReactNode }) {
  if (!children) return null;
  return (
    <p role={tone === "bad" ? "alert" : "status"} className={`rounded-md px-3 py-2 text-sm ring-1 ring-inset ${BADGE[tone]}`}>
      {children}
    </p>
  );
}

export function Loading({ what = "Loading" }: { what?: string }) {
  return <p className="py-6 text-sm text-gray-500">{what}…</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-gray-500">{children}</p>;
}

export type Column<T> = { key: string; label: string; render: (row: T) => ReactNode; align?: "right" | "left"; className?: string };

export function Table<T>({ rows, columns, rowKey, empty = "Nothing here yet.", onRowClick }: {
  rows: T[]; columns: Column<T>[]; rowKey: (row: T) => string; empty?: string; onRowClick?: (row: T) => void;
}) {
  if (rows.length === 0) return <Empty>{empty}</Empty>;
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="bg-[#F7F7F7] text-gray-500">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`px-5 py-3 font-medium ${c.align === "right" ? "text-right" : ""}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-t border-gray-100 ${onRowClick ? "cursor-pointer hover:bg-gray-50" : ""}`}>
              {columns.map((c) => (
                <td key={c.key} className={`px-5 py-3 align-top ${c.align === "right" ? "text-right tabular-nums" : ""} ${c.className ?? ""}`}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Modal({ open, title, onClose, children, wide }: { open: boolean; title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-xl bg-white p-5 shadow-xl sm:rounded-xl ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}>
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="rounded p-2 text-gray-500 hover:bg-gray-100" aria-label="Close">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Money({ paise, signed }: { paise: number | null | undefined; signed?: boolean }) {
  const value = paise ?? 0;
  const text = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Math.abs(value) / 100);
  if (!signed) return <span className="tabular-nums">{value < 0 ? `-${text}` : text}</span>;
  return <span className={`tabular-nums ${value < 0 ? "text-[#1E8E3E]" : value > 0 ? "text-[#D93025]" : ""}`}>{value < 0 ? `-${text}` : text}</span>;
}
