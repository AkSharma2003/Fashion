import { useState } from "react";
import { Alert, Badge, Button, Card, Input, Loading, Money, Page, Stat, Table } from "../../components/ui";
import { apiData, patch, post } from "../../lib/api/client";
import { hasRole, useStaff } from "../../lib/auth/staff";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { formatINR, rupeesToPaise } from "../../lib/money";

type Line = { id: string; employee_name: string; payable_days: number; earned_paise: number; incentive_paise: number;
  overtime_paise: number; advance_recovery_paise: number; other_deductions_paise: number; net_payable_paise: number };
type Run = { id: string; year: number; month: number; status: string; total_net_paise: number; lines: Line[] };

export default function PayrollPage() {
  const { me } = useStaff();
  const now = new Date();
  const [month, setMonth] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`);
  const [run, setRun] = useState<Run | null>(null);
  const runs = useApi(() => apiData<{ id: string; year: number; month: number; status: string }[]>("/payroll/runs"));
  const act = useAction();
  const locked = run?.status === "APPROVED";

  async function build() {
    const [y, m] = month.split("-").map(Number);
    const r = await act.run(() => post<Run>("/payroll/runs", { year: y, month: m }), "Draft worked out from attendance.");
    if (r) { setRun(r); void runs.reload(); }
  }

  async function edit(line: Line, field: keyof Line, value: string) {
    const paise = value === "" ? 0 : rupeesToPaise(value);
    if (Number.isNaN(paise) || !run) return;
    const updated = await act.run(() => patch<Line>(`/payroll/runs/${run.id}/lines/${line.id}`, { [field]: paise }));
    if (updated) {
      const lines = run.lines.map((l) => (l.id === line.id ? updated : l));
      setRun({ ...run, lines, total_net_paise: lines.reduce((s, l) => s + l.net_payable_paise, 0) });
    }
  }

  const money = (line: Line, field: keyof Line) => locked ? <Money paise={line[field] as number} /> : (
    <Input className="!min-h-9 w-24 text-right" inputMode="decimal" defaultValue={((line[field] as number) / 100).toString()}
      onBlur={(e) => void edit(line, field, e.target.value)} />);

  return (
    <Page title="Month-end salary" crumb="Salary" actions={<>
      <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" />
      <Button disabled={act.busy} onClick={() => void build()}>Work out salary</Button></>}>
      <Alert>{act.error}</Alert><Alert tone="good">{act.notice}</Alert>
      {run && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Month" value={`${String(run.month).padStart(2, "0")}/${run.year}`} />
            <Stat label="Total net payable" value={formatINR(run.total_net_paise)} />
            <Stat label="Status" value={<Badge>{run.status}</Badge>} note={locked ? "Locked after approval" : "Draft: check and approve"} />
          </div>
          <Card title="Salary sheet" actions={!locked && hasRole(me) && (
            <Button disabled={act.busy} onClick={async () => {
              if (!window.confirm("Approve and lock this month? Advance recoveries are then written.")) return;
              const r = await act.run(() => post<Run>(`/payroll/runs/${run.id}/approve`), "Approved and locked.");
              if (r) setRun(r);
            }}>Approve (owner)</Button>)}>
            <Table rows={run.lines} rowKey={(l) => l.id} columns={[
              { key: "n", label: "Employee", render: (l) => <span className="font-medium">{l.employee_name}</span> },
              { key: "d", label: "Days", align: "right", render: (l) => l.payable_days },
              { key: "e", label: "Earned", align: "right", render: (l) => <Money paise={l.earned_paise} /> },
              { key: "i", label: "Incentive", align: "right", render: (l) => money(l, "incentive_paise") },
              { key: "o", label: "Overtime", align: "right", render: (l) => money(l, "overtime_paise") },
              { key: "r", label: "Advance cut", align: "right", render: (l) => money(l, "advance_recovery_paise") },
              { key: "x", label: "Other cut", align: "right", render: (l) => money(l, "other_deductions_paise") },
              { key: "t", label: "Net", align: "right", render: (l) => <b><Money paise={l.net_payable_paise} /></b> },
            ]} />
          </Card>
        </>
      )}
      <Card title="Earlier months">
        {runs.loading && <Loading />}
        <Table rows={runs.data ?? []} rowKey={(r) => r.id} empty="No salary runs yet." onRowClick={async (r) => {
          const full = await act.run(() => apiData<Run>(`/payroll/runs/${r.id}`)); if (full) setRun(full); }} columns={[
          { key: "m", label: "Month", render: (r) => `${String(r.month).padStart(2, "0")}/${r.year}` },
          { key: "s", label: "Status", render: (r) => <Badge>{r.status}</Badge> },
        ]} />
      </Card>
    </Page>
  );
}
