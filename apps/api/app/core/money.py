"""Money is stored as an integer number of paise. Never use floats for money."""
from decimal import ROUND_HALF_UP, Decimal


def rupees_to_paise(value: str | int | float | Decimal) -> int:
    """'1499.50' -> 149950"""
    paise = (Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)


def _indian_grouping(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def format_inr(paise: int) -> str:
    """149900 -> '₹1,499.00', 123456700 -> '₹12,34,567.00', negatives get a minus sign."""
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(paise), 100)
    return f"{sign}₹{_indian_grouping(rupees)}.{rem:02d}"
