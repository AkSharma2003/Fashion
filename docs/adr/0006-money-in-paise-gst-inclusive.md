# ADR 0006: Money in paise, prices include GST

Status: accepted

- All amounts are integers in paise in the database, API and front end. No floats.
- Shelf prices include GST. Each bill line is split into taxable value and tax by `core/gst.split_inclusive`;
  the parts always add up to the line total.
- The GST rate is chosen per piece by price slab (`gst_slabs` setting: 5% up to ₹2,500, 18% above) unless the
  product has a fixed rate. Slabs are an assumption to confirm with the CA.
- Tax is split CGST + SGST. `split_inclusive` supports IGST (`inter_state=True`) but no caller uses it yet; other-
  state online orders need this before go-live if the CA requires it.
- Rates are stored in basis points (`gst_rate_bp`, 500 = 5%).

Why: rounding errors in money break the khata ledger, reconciliation with Tally, and customer trust.
