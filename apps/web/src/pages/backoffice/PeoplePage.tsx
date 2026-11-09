import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Modal, Money, Page, Select, Stat, Table } from "../../components/ui";
import { apiData, patch, post } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatINR, rupeesToPaise } from "../../lib/money";

type Employee = { id: string; full_name: string; phone: string; designation: string | null; pay_type: string; is_active: boolean;
  monthly_salary_paise?: number; daily_rate_paise?: number; advance_limit_paise?: number | null };
type Statement = { employee: Employee; year: number; month: number; status: string; attendance: Record<string, number>;
  payable_days: number; earned_paise: number; gross_paise: number; advance_recovery_paise: number; other_deductions_paise: number;
  net_payable_paise: number; paid_paise: number; pending_paise: number; advance_balance_paise: number; advance_balance_after_recovery_paise: number };

const STATUSES = [["P", "Present"], ["H", "Half day"], ["L", "Paid leave"], ["A", "Absent"], ["W", "Weekly off"]];

export default function PeoplePage() {
  const [tab, setTab] = useState<"attendance" | "staff">("attendance");
  return (
    <Page title="People" crumb="Employees" actions={
      <div className="flex gap-2">
        <Button variant={tab === "attendance" ? "primary" : "secondary"} onClick={() => setTab("attendance")}>Attendance</Button>
        <Button variant={tab === "staff" ? "primary" : "secondary"} onClick={() => setTab("staff")}>Staff</Button>
      </div>}>
      {tab === "attendance" ? <Attendance /> : <Staff />}
    </Page>
  );
}

function Attendance() {
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const data = useApi(() => apiData<{ employee_id: string; full_name: string; status: string | null }[]>(`/employees/attendance?day=${day}`), [day]);
  const [marks, setMarks] = useState<Record<string, string>>({});
  const act = useAction();
  useEffect(() => {
    setMarks(Object.fromEntries((data.data ?? []).map((r) => [r.employee_id, r.status ?? ""])));
  }, [data.data]);

  return (
    <Card title="Mark attendance" actions={<Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="w-44" />}>
      {data.loading && <Loading />}
      <Alert>{data.error || act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      <ul className="divide-y divide-gray-100">
        {(data.data ?? []).map((r) => (
          <li key={r.employee_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <span className="font-medium">{r.full_name}</span>
            <div className="flex flex-wrap gap-1">
              {STATUSES.map(([code, label]) => (
                <button key={code} type="button" onClick={() => setMarks({ ...marks, [r.employee_id]: code })}
                  className={`min-h-10 rounded-md border px-3 text-sm ${marks[r.employee_id] === code ? "border-[#111111] bg-[#111111] text-white" : "border-gray-300"}`}>{label}</button>
              ))}
            </div>
          </li>
        ))}
      </ul>
      {(data.data ?? []).length === 0 && !data.loading && <p className="text-sm text-gray-500">No active employees yet.</p>}
      <Button className="mt-4" disabled={act.busy || !data.data?.length} onClick={() => void act.run(() => post("/employees/attendance", {
        day, marks: Object.entries(marks).filter(([, s]) => s).map(([employee_id, status]) => ({ employee_id, status })) }), "Attendance saved.")}>Save attendance</Button>
    </Card>
  );
}

function Staff() {
  const { me } = useStaff();
  const canPay = hasRole(me, "Accountant");
  const list = useApi(() => apiData<Employee[]>("/employees?include_inactive=true"));
  const [sel, setSel] = useState<Employee | null>(null);
  const [adding, setAdding] = useState(false);
  return (
    <>
      <Card title="Employees" actions={canPay && <Button onClick={() => setAdding(true)}>Add employee</Button>}>
        <Alert>{list.error}</Alert>
        <Table rows={list.data ?? []} rowKey={(e) => e.id} onRowClick={canPay ? setSel : undefined} empty="No employees yet." columns={[
          { key: "n", label: "Name", render: (e) => <div><p className="font-medium">{e.full_name}</p><p className="text-xs text-gray-500">{e.phone} · {e.designation ?? "Staff"}</p></div> },
          { key: "t", label: "Pay", render: (e) => e.pay_type === "DAILY" ? "Daily" : "Monthly" },
          ...(canPay ? [{ key: "s", label: "Salary / rate", align: "right" as const, render: (e: Employee) => <Money paise={e.pay_type === "DAILY" ? e.daily_rate_paise : e.monthly_salary_paise} /> }] : []),
          { key: "a", label: "", render: (e) => !e.is_active && <Badge tone="info">left</Badge> },
        ]} />
      </Card>
      {adding && <EmployeeForm onClose={() => { setAdding(false); void list.reload(); }} />}
      {sel && <EmployeeModal emp={sel} onClose={() => { setSel(null); void list.reload(); }} />}
    </>
  );
}

function EmployeeForm({ onClose }: { onClose: () => void }) {
  const act = useAction();
  const [f, setF] = useState({ full_name: "", phone: "", designation: "", pay_type: "MONTHLY", amount: "", limit: "" });
  return (
    <Modal open title="Add employee" onClose={onClose}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
        <Field label="Phone"><Input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></Field>
        <Field label="Designation"><Input value={f.designation} onChange={(e) => setF({ ...f, designation: e.target.value })} /></Field>
        <Field label="Pay type"><Select value={f.pay_type} onChange={(e) => setF({ ...f, pay_type: e.target.value })}><option value="MONTHLY">Monthly</option><option value="DAILY">Daily</option></Select></Field>
        <Field label={f.pay_type === "DAILY" ? "Daily rate ₹" : "Monthly salary ₹"}><Input inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field>
        <Field label="Advance limit ₹ (optional)"><Input inputMode="decimal" value={f.limit} onChange={(e) => setF({ ...f, limit: e.target.value })} /></Field>
      </div>
      <div className="mt-4 space-y-2"><Alert>{act.error}</Alert>
        <Button disabled={act.busy} onClick={async () => {
          const paise = rupeesToPaise(f.amount);
          const ok = await act.run(() => post("/employees", { full_name: f.full_name, phone: f.phone, designation: f.designation || null, pay_type: f.pay_type,
            monthly_salary_paise: f.pay_type === "MONTHLY" ? paise : 0, daily_rate_paise: f.pay_type === "DAILY" ? paise : 0,
            advance_limit_paise: f.limit ? rupeesToPaise(f.limit) : null }));
          if (ok) onClose();
        }}>Save</Button></div>
    </Modal>
  );
}

function EmployeeModal({ emp, onClose }: { emp: Employee; onClose: () => void }) {
  const now = new Date();
  const st = useApi(() => apiData<Statement>(`/employees/${emp.id}/statement?year=${now.getFullYear()}&month=${now.getMonth() + 1}`), [emp.id]);
  const act = useAction();
  const [adv, setAdv] = useState({ amount: "", monthly: "", reason: "" });
  const [pay, setPay] = useState("");
  const s = st.data;
  return (
    <Modal open title={`${emp.full_name} · this month`} onClose={onClose} wide>
      {st.loading && <Loading />}
      {s && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Payable days" value={s.payable_days} note={`P ${s.attendance.P} · H ${s.attendance.H} · L ${s.attendance.L} · W ${s.attendance.W}`} />
            <Stat label="Net payable" value={formatINR(s.net_payable_paise)} note={`earned ${formatINR(s.earned_paise)} − recovery ${formatINR(s.advance_recovery_paise)}`} />
            <Stat label="Paid so far" value={formatINR(s.paid_paise)} />
            <Stat label="Pending" value={formatINR(s.pending_paise)} tone="warn" />
          </div>
          <p className="text-sm">Advance balance: <b>{formatINR(s.advance_balance_paise)}</b> (after this month's recovery: {formatINR(s.advance_balance_after_recovery_paise)}) · <Badge>{s.status}</Badge></p>
          <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Give advance">
              <div className="space-y-2">
                <Input placeholder="Amount ₹" inputMode="decimal" value={adv.amount} onChange={(e) => setAdv({ ...adv, amount: e.target.value })} />
                <Input placeholder="Monthly deduction ₹" inputMode="decimal" value={adv.monthly} onChange={(e) => setAdv({ ...adv, monthly: e.target.value })} />
                <Input placeholder="Reason" value={adv.reason} onChange={(e) => setAdv({ ...adv, reason: e.target.value })} />
                <Button disabled={act.busy} onClick={async () => {
                  await act.run(() => post(`/employees/${emp.id}/advances`, { amount_paise: rupeesToPaise(adv.amount), monthly_recovery_paise: rupeesToPaise(adv.monthly), reason: adv.reason }), "Advance saved.");
                  setAdv({ amount: "", monthly: "", reason: "" }); void st.reload(); }}>Save advance</Button>
              </div>
            </Card>
            <Card title="Record salary payment">
              <div className="space-y-2">
                <Input placeholder="Amount ₹" inputMode="decimal" value={pay} onChange={(e) => setPay(e.target.value)} />
                <Button disabled={act.busy || !rupeesToPaise(pay)} onClick={async () => {
                  await act.run(() => post(`/employees/${emp.id}/salary-payments`, { year: s.year, month: s.month, amount_paise: rupeesToPaise(pay) }), "Payment saved.");
                  setPay(""); void st.reload(); }}>Save payment</Button>
                <Button variant="secondary" onClick={async () => { await act.run(() => patch(`/employees/${emp.id}`, { is_active: !emp.is_active })); onClose(); }}>
                  {emp.is_active ? "Mark as left" : "Mark active"}</Button>
              </div>
            </Card>
          </div>
        </div>
      )}
    </Modal>
  );
}
