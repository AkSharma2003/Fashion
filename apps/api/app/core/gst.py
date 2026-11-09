"""GST is calculated on the server only (security checklist #10).

Shop prices are GST-inclusive. For each line we split the inclusive amount into
taxable value and tax, and split tax into CGST + SGST (intra-state) or IGST (inter-state).
All values are integer paise.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GstSplit:
    rate_bp: int          # 500 = 5.00 %
    taxable_paise: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int

    @property
    def tax_paise(self) -> int:
        return self.cgst_paise + self.sgst_paise + self.igst_paise


def rate_for_unit_price(unit_price_paise: int, slabs: list[dict], fixed_rate_bp: int | None = None) -> int:
    if fixed_rate_bp is not None:
        return fixed_rate_bp
    for slab in slabs:
        limit = slab.get("max_paise")
        if limit is None or unit_price_paise <= limit:
            return int(slab["rate_bp"])
    return int(slabs[-1]["rate_bp"]) if slabs else 0


def split_inclusive(amount_paise: int, rate_bp: int, inter_state: bool = False) -> GstSplit:
    if rate_bp <= 0 or amount_paise == 0:
        return GstSplit(rate_bp, amount_paise, 0, 0, 0)
    # taxable = amount * 10000 / (10000 + rate), rounded half up
    taxable = (amount_paise * 10000 * 2 + (10000 + rate_bp)) // (2 * (10000 + rate_bp))
    tax = amount_paise - taxable
    if inter_state:
        return GstSplit(rate_bp, taxable, 0, 0, tax)
    cgst = tax // 2
    return GstSplit(rate_bp, taxable, cgst, tax - cgst, 0)
