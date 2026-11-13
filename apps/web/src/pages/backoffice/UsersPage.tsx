import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Badge, Button, Card, Input, Loading, Money, Page, Select, Table } from "../../components/ui";
import { apiData, post } from "../../lib/api/client";
import { useConfirmChange } from "../../components/backoffice/ConfirmChange";
import { useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatDate } from "../../lib/money";

type Person = {
  id: string; full_name: string; phone_number: string; email: string | null; is_verified: boolean; is_active: boolean;
  has_password: boolean; joined: string | null;
  type: "khata" | "normal";
  khata: { account_id: string; balance_paise: number; credit_limit_paise: number; credit_days: number } | null;
  staff: { user_id: string; role: string | null; shop_id: string | null; is_active: boolean } | null;
};
type Listing = { can_give: string[]; users: Person[] };
type HistoryRow = { id: string; at: string | null; by: string; user: string; phone: string | null; change: string | null;
  from_role: string | null; to_role: string | null; reason: string | null };

const ROLE_LABEL: Record<string, string> = { OnlineStaff: "Online staff" };

/** Everyone who registered on the website. Owner / Admin / Manager can give them a staff role. */
export default function UsersPage() {
  const { me, shops } = useStaff();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<"" | "khata" | "normal">("");
  const list = useApi(() => {
    const qs = new URLSearchParams();
    if (search) qs.set("q", search);
    if (kind) qs.set("type", kind);
    return apiData<Listing>(`/auth/registered-users${qs.toString() ? `?${qs}` : ""}`);
  }, [search, kind]);
  const act = useAction();
  const { ask, dialog } = useConfirmChange();
  const history = useApi(() => apiData<HistoryRow[]>("/auth/role-history"));
  const [pick, setPick] = useState<Record<string, { role: string; shop: string }>>({});
  const canGive = list.data?.can_give ?? [];
  const staffCount = useMemo(() => (list.data?.users ?? []).filter((u) => u.staff?.is_active).length, [list.data]);
  const shopName = (id: string | null) => (id ? shops.find((s) => s.id === id)?.name ?? "—" : "All shops");

  async function give(u: Person) {
    const choice = pick[u.id] ?? { role: canGive[0], shop: me?.shop_id ?? "" };
    let password: string | null = null;
    if (!u.has_password && !u.staff) {
      password = window.prompt(`${u.full_name} has no password yet. Set a password for their staff login (min 6 characters):`);
      if (!password) return;
      if (password.length < 6) return act.setError("Password must be at least 6 characters.");
    }
    const from = u.staff?.is_active ? (ROLE_LABEL[u.staff.role ?? ""] ?? u.staff.role) : "Customer";
    const to = ROLE_LABEL[choice.role] ?? choice.role;
    const ok = await ask(`${u.full_name}: ${from} → ${to}`, { detail: <>Shop: <b>{shopName(choice.shop || null)}</b></> });
    if (!ok) return;
    const r = await act.run(() => post(`/auth/registered-users/${u.id}/role`, {
      role: choice.role, shop_id: choice.shop || null, ...(password ? { password } : {}), ...ok }),
      `${u.full_name} is now ${to}. They sign in at /login with their phone and password.`);
    if (r) { void list.reload(); void history.reload(); }
  }

  async function makeKhata(u: Person) {
    const limit = window.prompt(`Credit limit for ${u.full_name} (₹). Leave empty for the default in Settings:`, "");
    if (limit === null) return;
    const rupees = limit.trim() ? Number(limit.replace(/,/g, "")) : null;
    if (rupees !== null && (!Number.isFinite(rupees) || rupees < 0)) return act.setError("Enter the limit in rupees, e.g. 10000.");
    const r = await act.run(() => post(`/khata/customers/${u.id}/make-khata`,
      rupees === null ? {} : { credit_limit_paise: Math.round(rupees * 100) }), `${u.full_name} is now a khata customer.`);
    if (r) void list.reload();
  }

  async function makeNormal(u: Person) {
    if (!window.confirm(`Stop khata (credit) for ${u.full_name}? Their khata history is kept.`)) return;
    const r = await act.run(() => post(`/khata/customers/${u.id}/make-normal`), `${u.full_name} is now a normal customer.`);
    if (r) void list.reload();
  }

  async function remove(u: Person) {
    const ok = await ask(`Remove ${u.full_name}'s staff role`, { detail: "Their staff login is switched off. They stay a website customer." });
    if (!ok) return;
    const r = await act.run(() => post(`/auth/registered-users/${u.id}/role/remove`, ok), `${u.full_name} no longer has a staff role.`);
    if (r) { void list.reload(); void history.reload(); }
  }

  return (
    <Page title="Customers and users" crumb="Users" actions={
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setSearch(q.trim()); }}>
        <Input placeholder="Name, phone or e-mail" value={q} onChange={(e) => setQ(e.target.value)} className="w-56" />
        <Button type="submit" variant="secondary">Search</Button>
      </form>}>
      <p className="text-sm text-gray-600">
        Every customer is a <b>normal</b> customer until you make them a <b>khata</b> (credit) customer. Give someone a role to make them staff; they then sign in with the same
        phone and password and open their role's screens. {me?.role === "Manager" && "Managers can give Cashier, Online staff, Supervisor and Employee."}
      </p>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Customer type">
        {([["", "All"], ["normal", "Normal customers"], ["khata", "Khata customers"]] as const).map(([value, label]) => (
          <Button key={value} variant={kind === value ? "primary" : "secondary"} onClick={() => setKind(value)}>{label}</Button>
        ))}
      </div>
      <Alert>{act.error || list.error}</Alert>
      <Alert tone="good">{act.notice}</Alert>
      <Card title={list.data ? `${list.data.users.length} users · ${staffCount} with a staff role` : "Users"}>
        {list.loading && !list.data && <Loading />}
        <Table rows={list.data?.users ?? []} rowKey={(u) => u.id} empty="No registered users yet." columns={[
          { key: "n", label: "User", render: (u) => <div>
            <p className="font-medium">{u.full_name}</p>
            <p className="text-xs text-gray-500">{u.phone_number}{u.email ? ` · ${u.email}` : ""}</p></div> },
          { key: "j", label: "Joined", render: (u) => <div className="text-sm">{formatDate(u.joined)}
            {u.is_verified ? <span className="ml-1 text-xs text-[#1E8E3E]">✓ verified</span> : null}</div> },
          { key: "t", label: "Customer type", render: (u) => u.khata ? (
            <div>
              <Badge tone="warn">Khata</Badge>
              <p className="mt-1 text-xs text-gray-600">
                Owes <Money paise={u.khata.balance_paise} /> · limit <Money paise={u.khata.credit_limit_paise} />
              </p>
              <div className="mt-1 flex gap-3 text-xs">
                <Link className="underline" to={`/backoffice/khata?account=${u.khata.account_id}`}>Open khata</Link>
                <button type="button" className="text-gray-600 underline disabled:opacity-50" disabled={act.busy} onClick={() => void makeNormal(u)}>Make normal</button>
              </div>
            </div>
          ) : (
            <div>
              <Badge tone="info">Normal</Badge>
              <div className="mt-1"><button type="button" className="text-xs underline disabled:opacity-50" disabled={act.busy}
                onClick={() => void makeKhata(u)}>Make khata customer</button></div>
            </div>
          ) },
          { key: "r", label: "Staff role", render: (u) => u.staff?.is_active
            ? <div><Badge tone="good">{ROLE_LABEL[u.staff.role ?? ""] ?? u.staff.role}</Badge><p className="mt-1 text-xs text-gray-500">{shopName(u.staff.shop_id)}</p></div>
            : <span className="text-xs text-gray-500">{u.staff ? "Role removed" : "—"}</span> },
          { key: "a", label: "Give role", render: (u) => {
            const locked = u.staff?.is_active && u.staff.role && !canGive.includes(u.staff.role);
            if (locked) return <span className="text-xs text-gray-500">Only someone above can change this</span>;
            if (u.staff?.user_id && u.staff.user_id === me?.id) return <span className="text-xs text-gray-500">This is you</span>;
            const choice = pick[u.id] ?? { role: u.staff?.is_active && u.staff.role ? u.staff.role : canGive[0] ?? "", shop: u.staff?.shop_id ?? me?.shop_id ?? "" };
            return (
              <div className="flex flex-wrap items-center gap-2">
                <Select className="!min-h-9 w-36" value={choice.role} onChange={(e) => setPick({ ...pick, [u.id]: { ...choice, role: e.target.value } })}>
                  {canGive.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] ?? r}</option>)}
                </Select>
                <Select className="!min-h-9 w-40" value={choice.shop} disabled={Boolean(me?.shop_id)}
                  onChange={(e) => setPick({ ...pick, [u.id]: { ...choice, shop: e.target.value } })}>
                  {!me?.shop_id && <option value="">All shops</option>}
                  {shops.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </Select>
                <Button className="!min-h-9" disabled={act.busy || !choice.role} onClick={() => void give(u)}>
                  {u.staff?.is_active ? "Update" : "Give role"}
                </Button>
                {u.staff?.is_active && (
                  <Button className="!min-h-9" variant="secondary" disabled={act.busy} onClick={() => void remove(u)}>Remove role</Button>
                )}
              </div>
            );
          } },
        ]} />
      </Card>
      <Card title="Role change history">
        <p className="mb-3 text-xs text-gray-500">Every role or access change, with who did it and why. This record cannot be edited or deleted.</p>
        {history.loading && !history.data && <Loading />}
        <Table rows={history.data ?? []} rowKey={(h) => h.id} empty="No role changes yet." columns={[
          { key: "w", label: "When", render: (h) => formatDate(h.at, true) },
          { key: "u", label: "User", render: (h) => <div><p className="font-medium">{h.user}</p><p className="text-xs text-gray-500">{h.phone}</p></div> },
          { key: "c", label: "Change", render: (h) => h.change ?? `${h.from_role ?? "—"} → ${h.to_role ?? "—"}` },
          { key: "r", label: "Reason", render: (h) => <span className="text-sm">{h.reason || "—"}</span> },
          { key: "b", label: "Changed by", render: (h) => h.by },
        ]} />
      </Card>
      {dialog}
    </Page>
  );
}
