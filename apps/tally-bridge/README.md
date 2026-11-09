# WearVerse Tally bridge

Small Python agent that runs **on the same cloud Windows server as TallyPrime** (SRS 5.6).

- Opens **outbound HTTPS only** to the WearVerse API. Tally's local XML port (9000) is never opened to the internet.
- **WearVerse → Tally:** pulls `GET /api/v1/tally/outbox/pending`, builds Tally XML (Sales, Receipt, Credit Note,
  Purchase, Journal), posts it to Tally on `127.0.0.1:9000`, reports to `POST /api/v1/tally/outbox/{id}/result`.
  Every voucher carries a unique `WV-...` reference so a retry can never make a second voucher.
- **Tally → WearVerse (Mode A):** reads vouchers newer than the last `ALTERID` and sends them to
  `POST /api/v1/tally/inbox`. WearVerse turns them into bills, stock movements and khata entries, and skips
  anything with a `WV-` reference (it made those itself). Unmatched parties/items go to the Sync Issues screen.
- Sends a heartbeat each cycle; the API alerts if vouchers wait longer than 30 minutes.

## Run

```bash
pip install -r requirements.txt
copy config\config.example.yaml config\tally-bridge.local.yaml   # then edit api_key, company_name
python src/agent.py --test-tally   # check Tally answers on port 9000
python src/agent.py --once         # one cycle
python src/agent.py                # keep running
```

Install as a service: `installer\install-service.ps1` (NSSM). Set the same key as `TALLY_AGENT_API_KEY` in the API.

## Verify in Sprint 0 (on a **test company**, never the real data)

- Exact TallyPrime version, and that XML/HTTP access is on (F1 → Settings → Connectivity).
- Debit/credit sign convention in `voucher_builder.build_voucher` (debit = `ISDEEMEDPOSITIVE Yes`, negative amount).
- Field names in `tally_reader.py` (`ALLINVENTORYENTRIES.LIST`, `BILLEDQTY`) for the installed version.
- Ledger names: map them in WearVerse → Tally → Mappings before switching to the real company.
