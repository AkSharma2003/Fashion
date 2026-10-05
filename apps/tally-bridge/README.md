# Tally bridge

Small Windows program that runs on the PC where Tally is installed.

- Opens **outbound HTTPS only** to the FashionOS API (no open port on the shop network).
- Pulls pending vouchers from `GET /api/v1/tally/outbox/pending`, posts them to Tally on the same PC,
  and reports the result to `POST /api/v1/tally/outbox/{id}/result`.
- Reads new or changed vouchers and stock from Tally and sends them to `POST /api/v1/tally/inbox`.
- Every voucher carries a unique FashionOS reference so a retry never makes a second voucher.

Status: skeleton only. First task (Sprint 0): confirm the Tally version and which local interface it offers,
then test with a **demo company**.
