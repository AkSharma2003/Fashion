# ADR 0003: Outbox, offline POS and idempotency

Status: accepted

- Tally and WhatsApp work is saved in an outbox table in the same transaction as the sale, then sent by workers.
- The POS keeps bills locally when offline; each bill has an idempotency key (counter + bill number).
- Money ledgers (khata, salary, fall-pico wages), stock movements and audit logs are append-only.
- The existing shop keeps selling during rollout: Mode A (coexistence, import from Tally) then Mode B (FashionOS POS).
  See SRS section 3.18.
