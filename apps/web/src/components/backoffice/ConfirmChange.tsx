import { useRef, useState, type ReactNode } from "react";
import { Button, Field, Input, Modal } from "../ui";

export type Confirmed = { confirm_password: string; reason: string };

/** Asks the person making a role / access change for a reason and their own password.
 *  `const { ask, dialog } = useConfirmChange();  const ok = await ask("Make Asha a Cashier");  {dialog}` */
export function useConfirmChange() {
  const [open, setOpen] = useState<{ title: string; detail?: ReactNode; needReason: boolean } | null>(null);
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");
  const resolver = useRef<(v: Confirmed | null) => void>();

  function ask(title: string, opts: { detail?: ReactNode; needReason?: boolean } = {}): Promise<Confirmed | null> {
    setReason("");
    setPassword("");
    setOpen({ title, detail: opts.detail, needReason: opts.needReason ?? true });
    return new Promise((resolve) => { resolver.current = resolve; });
  }

  function finish(value: Confirmed | null) {
    resolver.current?.(value);
    resolver.current = undefined;
    setOpen(null);
    setPassword("");
  }

  const reasonOk = !open?.needReason || reason.trim().length >= 5;
  const dialog = (
    <Modal open={Boolean(open)} title={open?.title ?? ""} onClose={() => finish(null)}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (reasonOk && password) finish({ confirm_password: password, reason: reason.trim() }); }}>
        {open?.detail && <div className="text-sm text-gray-600">{open.detail}</div>}
        <Field label={open?.needReason ? "Reason for this change" : "Reason (optional)"}
          hint="Saved in the role history with your name and the time.">
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} maxLength={300} autoFocus
            required={open?.needReason} placeholder="e.g. Joined the counter team / Moved to accounts / Left the job"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#111111]" />
        </Field>
        <Field label="Your password" hint="To confirm it is really you making this change.">
          <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {open?.needReason && reason.length > 0 && !reasonOk && <p className="text-xs text-red-700">Write at least 5 characters.</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => finish(null)}>Cancel</Button>
          <Button type="submit" disabled={!reasonOk || !password}>Confirm change</Button>
        </div>
      </form>
    </Modal>
  );
  return { ask, dialog };
}
