import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Field, Input, Loading, Page } from "../../components/ui";
import { apiData, patch } from "../../lib/api/client";
import StaffLogins from "../../components/backoffice/StaffLogins";
import ShopsCard from "../../components/backoffice/ShopsCard";
import { useAction, useApi } from "../../lib/hooks/useApi";
import { rupeesToPaise } from "../../lib/money";

type Settings = { rules: Record<string, unknown>; integrations: Record<string, boolean | string> };

const MONEY_RULES: [string, string][] = [
  ["fall_pico_limit_paise", "Fall-pico on sarees priced above ₹"],
  ["khata_default_limit_paise", "Default khata limit ₹"],
  ["advance_limit_paise", "Employee advance limit ₹"],
  ["shipping_fee_paise", "Website shipping fee ₹"],
  ["free_shipping_above_paise", "Free shipping above ₹ (0 = never)"],
];
const NUMBER_RULES: [string, string][] = [
  ["khata_default_credit_days", "Default credit days"],
  ["khata_offline_limit_percent", "Offline credit limit (% of limit)"],
  ["fall_pico_default_days", "Fall-pico promise (days)"],
  ["reservation_minutes", "Hold unpaid website stock (minutes)"],
  ["return_days", "Return window (days)"],
  ["paylink_valid_days", "Pay Now link valid (days)"],
  ["tally_alert_after_minutes", "Alert if Tally waits (minutes)"],
];

export default function SettingsPage() {
  const settings = useApi(() => apiData<Settings>("/settings"));
  const act = useAction();
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!settings.data) return;
    const r = settings.data.rules;
    const d: Record<string, string> = { shop_name: String(r.shop_name ?? ""), shop_gstin: String(r.shop_gstin ?? "") };
    MONEY_RULES.forEach(([k]) => { d[k] = String(Number(r[k] ?? 0) / 100); });
    NUMBER_RULES.forEach(([k]) => { d[k] = String(r[k] ?? ""); });
    setDraft(d);
  }, [settings.data]);

  async function saveRules() {
    const body: Record<string, unknown> = { shop_name: draft.shop_name, shop_gstin: draft.shop_gstin };
    MONEY_RULES.forEach(([k]) => { body[k] = rupeesToPaise(draft[k] || "0"); });
    NUMBER_RULES.forEach(([k]) => { body[k] = Number(draft[k]); });
    if (Object.values(body).some((v) => typeof v === "number" && Number.isNaN(v))) return act.setError("Check the numbers.");
    await act.run(() => patch("/settings", body), "Rules saved.");
  }

  return (
    <Page title="Settings" crumb="Owner only">
      {settings.loading && <Loading />}
      <Alert>{act.error || settings.error}</Alert><Alert tone="good">{act.notice}</Alert>
      {settings.data && (
        <>
          <Card title="Rules" actions={<Button disabled={act.busy} onClick={() => void saveRules()}>Save rules</Button>}>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <Field label="Shop name"><Input value={draft.shop_name ?? ""} onChange={(e) => setDraft({ ...draft, shop_name: e.target.value })} /></Field>
              <Field label="GSTIN"><Input value={draft.shop_gstin ?? ""} onChange={(e) => setDraft({ ...draft, shop_gstin: e.target.value })} /></Field>
              {[...MONEY_RULES, ...NUMBER_RULES].map(([k, label]) => (
                <Field key={k} label={label}><Input inputMode="decimal" value={draft[k] ?? ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} /></Field>
              ))}
            </div>
          </Card>
          <Card title="Connections">
            <div className="flex flex-wrap gap-2">
              {Object.entries(settings.data.integrations).map(([k, v]) => (
                <span key={k} className="text-sm">{k.replace(/_/g, " ")}: {typeof v === "boolean" ? <Badge tone={v ? "good" : "warn"}>{v ? "connected" : "not set"}</Badge> : <code>{v}</code>}</span>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500">Keys are set in the server's environment (secrets manager), never on this screen.</p>
          </Card>
        </>
      )}
      <ShopsCard />
      <StaffLogins />
    </Page>
  );
}
