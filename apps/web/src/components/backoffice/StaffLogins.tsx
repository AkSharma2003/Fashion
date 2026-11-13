import { useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Select, Table } from "../ui";
import { apiData, patch, post } from "../../lib/api/client";
import { useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { navigation } from "../../routes/backoffice/BackofficeLayout";
import { useConfirmChange } from "./ConfirmChange";

type User = { id: string; full_name: string; phone_number: string; email: string | null; role: string | null; is_active: boolean; has_pin: boolean;
  shop_id: string | null };
type Employee = { id: string; full_name: string; staff_user_id: string | null; is_active: boolean };

/** What each role is for. The screens each role opens come from the back-office menu itself. */
const ROLE_INFO: Record<string, string> = {
  Owner: "Everything, including Settings, staff logins, write-offs and salary approval.",
  Admin: "Everything an Owner can, except giving the Owner role.",
  Manager: "Runs the shop: billing, stock, khata, online orders, fall-pico, buying. Approves with PIN.",
  Cashier: "Counter billing (POS), returns, khata payments, stock look-up.",
  Accountant: "Khata, bills, salary, Tally, reports and buying.",
  OnlineStaff: "Website orders, packing, shipping, products and stock.",
  Supervisor: "Fall-pico job board and workers.",
  Employee: "Only their own attendance and salary statement.",
};
const PIN_ROLES = ["Owner", "Admin", "Manager"];
const EMPTY = { full_name: "", phone_number: "", role: "Cashier", password: "", pin: "", employee_id: "", shop_id: "" };

function screensFor(role: string): string[] {
  if (role === "Owner" || role === "Admin") return navigation.map((n) => n.name);
  return navigation.filter((n) => n.roles.includes(role)).map((n) => n.name);
}

/** Settings → Staff logins: who can sign in, with which role, linked to which employee. */
export default function StaffLogins() {
  const { me, shops } = useStaff();
  const users = useApi(() => apiData<User[]>("/auth/users"));
  const roles = useApi(() => apiData<string[]>("/auth/roles"));
  const employees = useApi(() => apiData<Employee[]>("/employees?include_inactive=true").catch(() => [] as Employee[]));
  const act = useAction();
  const { ask, dialog } = useConfirmChange();
  const [nu, setNu] = useState(EMPTY);
  const [showGuide, setShowGuide] = useState(false);
  const isOwner = me?.role === "Owner";
  const roleList = (roles.data ?? []).filter((r) => isOwner || r !== "Owner");
  const linkedTo = (userId: string) => employees.data?.find((e) => e.staff_user_id === userId);
  const freeEmployees = (employees.data ?? []).filter((e) => e.is_active && !e.staff_user_id);

  async function reloadAll() {
    await Promise.all([users.reload(), employees.reload()]);
  }

  async function create() {
    if (!/^\d{10}$/.test(nu.phone_number)) return act.setError("Phone number must be 10 digits.");
    if (nu.password.length < 6) return act.setError("Password must be at least 6 characters.");
    if (PIN_ROLES.includes(nu.role) && nu.pin && !/^\d{4,6}$/.test(nu.pin)) return act.setError("PIN must be 4 to 6 digits.");
    const ok = await ask(`New login: ${nu.full_name.trim()} as ${nu.role}`, { needReason: false });
    if (!ok) return;
    const created = await act.run(() => post<User>("/auth/users", {
      full_name: nu.full_name.trim(), phone_number: nu.phone_number, role: nu.role, password: nu.password,
      pin: PIN_ROLES.includes(nu.role) && nu.pin ? nu.pin : null, shop_id: nu.shop_id || null, ...ok }),
      "Login created. They can sign in at /login with this phone and password.");
    if (created && nu.employee_id) {
      await act.run(() => patch(`/employees/${nu.employee_id}`, { staff_user_id: created.id }));
    }
    if (created) { setNu(EMPTY); void reloadAll(); }
  }

  async function change(u: User, body: Record<string, unknown>, done: string) {
    // Role, shop or on/off changes need a reason and the changer's own password (kept in the role history).
    const access = "role" in body || "shop_id" in body || "all_shops" in body || "is_active" in body;
    let extra = {};
    if (access) {
      const ok = await ask(`${u.full_name}: ${done.replace(/\.$/, "")}`);
      if (!ok) { void users.reload(); return; }
      extra = ok;
    }
    await act.run(() => patch(`/auth/users/${u.id}`, { ...body, ...extra }), done);
    void users.reload();
  }

  async function link(u: User, employeeId: string) {
    const current = linkedTo(u.id);
    if (current && current.id !== employeeId) await act.run(() => patch(`/employees/${current.id}`, { staff_user_id: null }));
    if (employeeId) await act.run(() => patch(`/employees/${employeeId}`, { staff_user_id: u.id }), "Employee linked. They now see their own statement.");
    else act.setNotice("Employee unlinked.");
    void employees.reload();
  }

  return (
    <Card title="Staff logins" actions={<Button variant="secondary" onClick={() => setShowGuide(!showGuide)}>{showGuide ? "Hide" : "What each role can open"}</Button>}>
      <Alert>{act.error}</Alert>
      <Alert tone="good">{act.notice}</Alert>

      {showGuide && (
        <div className="mb-5 overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50"><tr><th className="p-3">Role</th><th className="p-3">For</th><th className="p-3">Screens</th></tr></thead>
            <tbody className="divide-y divide-gray-100">
              {Object.keys(ROLE_INFO).map((r) => (
                <tr key={r}>
                  <td className="p-3 font-medium">{r}</td>
                  <td className="p-3 text-gray-600">{ROLE_INFO[r]}</td>
                  <td className="p-3"><div className="flex flex-wrap gap-1">{screensFor(r).map((s) => <Badge key={s} tone="info">{s}</Badge>)}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4" onSubmit={(e) => { e.preventDefault(); void create(); }}>
        <p className="mb-3 font-medium">Add a login</p>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Name"><Input required minLength={2} maxLength={50} value={nu.full_name} onChange={(e) => setNu({ ...nu, full_name: e.target.value })} /></Field>
          <Field label="Mobile number (used to sign in)"><Input required inputMode="numeric" maxLength={10} value={nu.phone_number}
            onChange={(e) => setNu({ ...nu, phone_number: e.target.value.replace(/\D/g, "") })} /></Field>
          <Field label="Role" hint={ROLE_INFO[nu.role]}>
            <Select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}>{roleList.map((r) => <option key={r}>{r}</option>)}</Select>
          </Field>
          <Field label="Password (min 6)"><Input required type="password" minLength={6} autoComplete="new-password" value={nu.password}
            onChange={(e) => setNu({ ...nu, password: e.target.value })} /></Field>
          {PIN_ROLES.includes(nu.role) && (
            <Field label="Approval PIN (4–6 digits)" hint="Used to approve discounts and credit at the counter."><Input type="password" inputMode="numeric" maxLength={6} value={nu.pin}
              onChange={(e) => setNu({ ...nu, pin: e.target.value.replace(/\D/g, "") })} /></Field>
          )}
          <Field label="Shop" hint="Staff of one shop only see and bill for that shop. Owner and accountant: all shops.">
            <Select value={nu.shop_id} onChange={(e) => setNu({ ...nu, shop_id: e.target.value })}>
              <option value="">All shops</option>
              {shops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </Select>
          </Field>
          <Field label="Employee record (optional)" hint="Link so they can see their own salary statement.">
            <Select value={nu.employee_id} onChange={(e) => setNu({ ...nu, employee_id: e.target.value })}>
              <option value="">Not linked</option>
              {freeEmployees.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}
            </Select>
          </Field>
        </div>
        <Button className="mt-4" type="submit" disabled={act.busy}>Create login</Button>
      </form>

      <Table rows={users.data ?? []} rowKey={(u) => u.id} empty="No staff logins yet." columns={[
        { key: "n", label: "Name", render: (u) => <div>
          <p className="font-medium">{u.full_name} {u.id === me?.id && <Badge tone="info">you</Badge>}</p>
          <p className="text-xs text-gray-500">{u.phone_number}</p></div> },
        { key: "r", label: "Role", render: (u) => {
          const locked = u.id === me?.id || (u.role === "Owner" && !isOwner);
          return <Select className="!min-h-9 w-36" disabled={locked || act.busy} title={locked ? "You cannot change this role" : undefined}
            value={u.role ?? ""} onChange={(e) => void change(u, { role: e.target.value }, `${u.full_name} is now ${e.target.value}.`)}>
            {(locked ? (roles.data ?? []) : roleList).map((r) => <option key={r}>{r}</option>)}</Select>; } },
        { key: "s", label: "Shop", render: (u) => (
          <Select className="!min-h-9 w-44" value={u.shop_id ?? ""} disabled={act.busy || u.id === me?.id}
            onChange={(e) => void change(u, e.target.value ? { shop_id: e.target.value } : { all_shops: true },
              e.target.value ? `${u.full_name} now works in ${shops.find((s) => s.id === e.target.value)?.name}.` : `${u.full_name} now works in all shops.`)}>
            <option value="">All shops</option>
            {shops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>) },
        { key: "e", label: "Employee record", render: (u) => {
          const current = linkedTo(u.id);
          return <Select className="!min-h-9 w-44" value={current?.id ?? ""} disabled={act.busy} onChange={(e) => void link(u, e.target.value)}>
            <option value="">Not linked</option>
            {current && <option value={current.id}>{current.full_name}</option>}
            {freeEmployees.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}
          </Select>; } },
        { key: "p", label: "PIN", render: (u) => PIN_ROLES.includes(u.role ?? "")
          ? <div className="flex items-center gap-2">{u.has_pin ? <Badge tone="good">set</Badge> : <Badge tone="warn">none</Badge>}
              <button type="button" className="text-xs underline" onClick={() => {
                const pin = window.prompt(`New approval PIN for ${u.full_name} (4–6 digits):`);
                if (pin && /^\d{4,6}$/.test(pin)) void change(u, { pin }, "PIN changed.");
                else if (pin) act.setError("PIN must be 4 to 6 digits.");
              }}>{u.has_pin ? "Change" : "Set"}</button></div>
          : <span className="text-xs text-gray-400">—</span> },
        { key: "a", label: "", render: (u) => (
          <div className="flex flex-wrap justify-end gap-2">
            <Button className="!min-h-9" variant="secondary" disabled={act.busy} onClick={() => {
              const pw = window.prompt(`New password for ${u.full_name} (min 6 characters):`);
              if (pw && pw.length >= 6) void change(u, { password: pw }, "Password changed. Tell them the new one.");
              else if (pw) act.setError("Password must be at least 6 characters.");
            }}>Reset password</Button>
            {u.id !== me?.id && (
              <Button className="!min-h-9" variant="secondary" disabled={act.busy}
                onClick={() => void change(u, { is_active: !u.is_active }, u.is_active ? `${u.full_name} can no longer sign in.` : `${u.full_name} can sign in again.`)}>
                {u.is_active ? "Switch off" : "Switch on"}</Button>
            )}
          </div>) },
      ]} />
      {dialog}
    </Card>
  );
}
