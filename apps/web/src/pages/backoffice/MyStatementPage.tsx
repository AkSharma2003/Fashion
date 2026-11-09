import { useState } from "react";
import { Alert, Badge, Card, Input, Loading, Page, Stat } from "../../components/ui";
import { apiData } from "../../lib/api/client";
import { useApi } from "../../lib/hooks/useApi";
import { formatINR } from "../../lib/money";
import { useT } from "../../lib/i18n";

type Statement = { employee: { full_name: string }; status: string; attendance: Record<string, number>; payable_days: number;
  earned_paise: number; advance_recovery_paise: number; net_payable_paise: number; paid_paise: number; pending_paise: number;
  advance_balance_paise: number };

/** Simple page: an employee sees only their own attendance, salary, advance and balance (T21). */
export default function MyStatementPage() {
  const { t } = useT();
  const now = new Date();
  const [month, setMonth] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`);
  const [y, m] = month.split("-").map(Number);
  const st = useApi(() => apiData<Statement>(`/payroll/me/statement?year=${y}&month=${m}`), [month]);
  const s = st.data;
  return (
    <Page title={t("My salary")} crumb="My statement" actions={<Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" />}>
      {st.loading && <Loading />}
      <Alert tone="warn">{st.error && "Your login is not linked to an employee record yet. Ask the owner."}</Alert>
      {s && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label={t("Days to be paid")} value={s.payable_days} />
            <Stat label={t("Salary this month")} value={formatINR(s.net_payable_paise)} note={`after advance cut ${formatINR(s.advance_recovery_paise)}`} />
            <Stat label={t("Already paid")} value={formatINR(s.paid_paise)} tone="good" />
            <Stat label={t("Still to get")} value={formatINR(s.pending_paise)} tone="warn" />
          </div>
          <Card title={t("Attendance")}>
            <p className="text-lg">Present {s.attendance.P} · Half day {s.attendance.H} · Leave {s.attendance.L} · Absent {s.attendance.A} · Weekly off {s.attendance.W}</p>
            <p className="mt-3 text-lg">{t("Advance left to repay")}: <b>{formatINR(s.advance_balance_paise)}</b> <Badge>{s.status}</Badge></p>
          </Card>
        </>
      )}
    </Page>
  );
}
