# Tally bridge runbook

The bridge (`apps/tally-bridge`) runs on the Windows server that runs TallyPrime. It only makes **outbound**
HTTPS calls to the WearVerse API; Tally's XML port (9000) stays closed to the internet. Developer details:
[apps/tally-bridge/README.md](../../apps/tally-bridge/README.md).

Always work on a **test company** until the accountant approves the vouchers.

## Install

1. In TallyPrime: F1 (Help) → Settings → Connectivity → client/server: **Both**, port **9000**. Keep the
   company open; the bridge talks to the loaded company.
2. Install Python 3.11 and copy `apps/tally-bridge` to e.g. `C:\wearverse\tally-bridge`.
3. `pip install -r requirements.txt`
4. `copy config\config.example.yaml config\tally-bridge.local.yaml` and set:
   - `api_base_url`: `https://<domain>/api/v1`
   - `api_key`: the API's `TALLY_AGENT_API_KEY`
   - `company_name`: exactly as in Tally
   - `read_from_tally: true` for Mode A
5. Test: `python src/agent.py --test-tally` (Tally answers), then `python src/agent.py --once` (one cycle).
6. Install the service (Administrator PowerShell, NSSM in `C:\nssm`):
   `installer\install-service.ps1`. The service **WearVerseTallyBridge** starts with Windows and keeps running
   after logout.

## What it does every 15 seconds

1. Heartbeat → `POST /tally/heartbeat` (shown in Tally → Sync status).
2. WearVerse → Tally: fetch `GET /tally/outbox/pending`, build XML (Sales, Receipt, Credit Note, Purchase,
   Journal), post to Tally, report `POST /tally/outbox/{id}/result`. Each voucher has a unique `WV-...`
   reference so a retry cannot create a second voucher.
3. Tally → WearVerse (Mode A): read vouchers with `ALTERID` above the last one seen and send them to
   `POST /tally/inbox`.

## Checks

| Question | Where |
|---|---|
| Is the bridge alive? | Back office → Tally → Sync status: last heartbeat within a minute |
| Is anything stuck? | Same page: waiting vouchers, oldest age; alert after 30 minutes |
| What failed? | Tally → Sync issues (reason, message, Retry / Resolve) |
| Log | `C:\wearverse\tally-bridge\logs\bridge.log` |

## When things go wrong

| Symptom | Cause | Fix |
|---|---|---|
| Heartbeat old, log says connection refused to 127.0.0.1:9000 | Tally closed or company not loaded | Open Tally and the company. The bridge retries by itself; waiting items go in order with no duplicates (T38) |
| Heartbeat old, nothing in the log | Service stopped | `nssm restart WearVerseTallyBridge` (or Services → WearVerseTallyBridge → Restart) |
| Log says 401 from the API | Key mismatch | Same value in `tally-bridge.local.yaml` and the API's `TALLY_AGENT_API_KEY`; restart the service |
| Sync issue "ledger not found" / "item not found" | Name not mapped | Tally → Mappings: map the WearVerse customer / item to the Tally name, then Retry |
| Sync issue "unknown party" on an imported voucher (Mode A) | Customer in Tally is not in WearVerse | Map the Tally ledger to a WearVerse customer (by phone), Retry. No message was sent to anyone (T36) |
| Voucher posted with wrong sign | Debit/credit convention differs for this Tally version | Fix `voucher_builder.build_voucher` on the test company first |
| Tally unreachable over 30 minutes | Server or network down | Alert is raised; items wait; counter uses POS (Mode B) or the paper bill book (T39, T40) |

## Upgrading the bridge

Stop the service, replace the `src` folder, `pip install -r requirements.txt`, start the service. The last
`ALTERID` read is kept by the API, so nothing is read twice.
