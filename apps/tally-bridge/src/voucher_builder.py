"""Build Tally XML vouchers from normalized WearVerse payloads."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape


def _money(
    value: int | float | str | Decimal
) -> str:

    amount = Decimal(str(value))

    if amount == amount.to_integral_value():
        return str(int(amount))

    return format(amount, "f")


def build_sales_voucher(
    *,
    reference: str,
    voucher_date: str | date,
    customer_name: str,
    amount: int | float | str | Decimal,
    company_name: str,
    party_ledger: str | None = None,
    sales_ledger: str = "Sales",
) -> str:

    """
    Create a basic accounting sales voucher.

    The party and sales ledger must already exist in Tally.
    """

    if isinstance(voucher_date, date):

        tally_date = voucher_date.strftime(
            "%Y%m%d"
        )

    else:

        tally_date = voucher_date.replace(
            "-",
            ""
        )

    party = party_ledger or customer_name

    amount_text = _money(amount)

    fields = {
        "company_name": escape(company_name),
        "reference": escape(reference),
        "customer_name": escape(customer_name),
        "party": escape(party),
        "sales_ledger": escape(sales_ledger),
    }

    return f"""<ENVELOPE>

  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Import</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>

  <BODY>

    <DESC>

      <STATICVARIABLES>
        <SVCURRENTCOMPANY>
          {fields['company_name']}
        </SVCURRENTCOMPANY>
      </STATICVARIABLES>

    </DESC>

    <DATA>

      <TALLYMESSAGE xmlns:UDF="TallyUDF">

        <VOUCHER
          VCHTYPE="Sales"
          ACTION="Create"
          OBJVIEW="Accounting Voucher View"
          REMOTEID="{fields['reference']}">

          <DATE>{tally_date}</DATE>

          <VOUCHERTYPENAME>
            Sales
          </VOUCHERTYPENAME>

          <PARTYLEDGERNAME>
            {fields['party']}
          </PARTYLEDGERNAME>

          <REFERENCE>
            {fields['reference']}
          </REFERENCE>

          <PERSISTEDVIEW>
            Accounting Voucher View
          </PERSISTEDVIEW>

          <ISINVOICE>
            Yes
          </ISINVOICE>

          <LEDGERENTRIES.LIST>

            <LEDGERNAME>
              {fields['party']}
            </LEDGERNAME>

            <ISDEEMEDPOSITIVE>
              No
            </ISDEEMEDPOSITIVE>

            <AMOUNT>
              {amount_text}
            </AMOUNT>

          </LEDGERENTRIES.LIST>


          <LEDGERENTRIES.LIST>

            <LEDGERNAME>
              {fields['sales_ledger']}
            </LEDGERNAME>

            <ISDEEMEDPOSITIVE>
              Yes
            </ISDEEMEDPOSITIVE>

            <AMOUNT>
              -{amount_text}
            </AMOUNT>

          </LEDGERENTRIES.LIST>

        </VOUCHER>

      </TALLYMESSAGE>

    </DATA>

  </BODY>

</ENVELOPE>"""


def parse_import_response(
    xml_text: str
) -> tuple[bool, str]:

    """
    Interpret the standard Tally import response.
    """

    import xml.etree.ElementTree as ET

    try:

        root = ET.fromstring(xml_text)

    except ET.ParseError:

        return (
            False,
            "Tally returned non-XML response: "
            + xml_text[:500]
        )

    def values(name: str) -> list[str]:

        return [
            (element.text or "").strip()
            for element in root.iter()
            if element.tag.upper().split("}")[-1]
            == name.upper()
        ]

    errors = values("ERRORS")

    line_errors = values(
        "LINEERROR"
    )

    created = values(
        "CREATED"
    )

    altered = values(
        "ALTERED"
    )

    if any(
        value not in {"", "0"}
        for value in errors + line_errors
    ):

        detail = "; ".join(
            value
            for value in errors + line_errors
            if value
        )

        return (
            False,
            detail
            or "Tally reported an import error"
        )

    if any(
        value not in {"", "0"}
        for value in created + altered
    ):

        return (
            True,
            f"Tally accepted voucher "
            f"(created={created or ['0']}, "
            f"altered={altered or ['0']})"
        )

    return (
        True,
        "Tally accepted the XML request"
    )

# ---- Generic accounting vouchers (all WearVerse voucher types) ------------------------------
#
# Tally XML convention: a DEBIT line has ISDEEMEDPOSITIVE=Yes and a negative AMOUNT,
# a CREDIT line has ISDEEMEDPOSITIVE=No and a positive AMOUNT.
# [Verify on the TallyPrime test company in Sprint 0 before switching to the real company.]

def _tally_date(value) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    return str(value or date.today().isoformat()).replace("-", "")[:8]


def build_voucher(*, voucher_type: str, reference: str, voucher_date, company_name: str,
                  party_ledger: str | None, lines: list[tuple[str, Decimal]], narration: str = "") -> str:
    """lines: (ledger name, signed amount) with + = debit and - = credit. Must add up to zero."""
    total = sum((Decimal(str(a)) for _, a in lines), Decimal("0"))
    if total != 0:
        raise ValueError(f"Voucher {reference} does not balance (difference {total}).")
    entries = []
    for ledger, amount in lines:
        amount = Decimal(str(amount))
        if amount == 0:
            continue
        debit = amount > 0
        entries.append(
            "<ALLLEDGERENTRIES.LIST>"
            f"<LEDGERNAME>{escape(ledger)}</LEDGERNAME>"
            f"<ISDEEMEDPOSITIVE>{'Yes' if debit else 'No'}</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{'-' if debit else ''}{_money(abs(amount))}</AMOUNT>"
            "</ALLLEDGERENTRIES.LIST>")
    party_xml = f"<PARTYLEDGERNAME>{escape(party_ledger)}</PARTYLEDGERNAME>" if party_ledger else ""
    return (
        "<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Import</TALLYREQUEST><TYPE>Data</TYPE>"
        "<ID>Vouchers</ID></HEADER><BODY><DESC><STATICVARIABLES>"
        f"<SVCURRENTCOMPANY>{escape(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES></DESC><DATA>"
        '<TALLYMESSAGE xmlns:UDF="TallyUDF">'
        f'<VOUCHER VCHTYPE="{escape(voucher_type)}" ACTION="Create" REMOTEID="{escape(reference)}">'
        f"<DATE>{_tally_date(voucher_date)}</DATE>"
        f"<VOUCHERTYPENAME>{escape(voucher_type)}</VOUCHERTYPENAME>"
        f"<VOUCHERNUMBER>{escape(reference)}</VOUCHERNUMBER>"
        f"<REFERENCE>{escape(reference)}</REFERENCE>"
        f"<NARRATION>{escape(narration or reference)}</NARRATION>"
        f"{party_xml}{''.join(entries)}"
        "</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>")


def _d(value) -> Decimal:
    return Decimal(str(value or "0"))


def voucher_from_event(event_type: str, payload: dict, company_name: str) -> str:
    """Turn a WearVerse outbox payload into Tally XML."""
    ref = str(payload["reference"])
    vdate = payload.get("voucher_date")
    amount = _d(payload.get("amount"))
    party = payload.get("party_ledger") or payload.get("customer_name")

    if event_type == "sales_voucher":
        sales = payload.get("sales_ledger") or "Sales"
        if payload.get("cgst") is not None or payload.get("tax") is not None:
            if payload.get("cgst") is not None:
                cgst, sgst = _d(payload.get("cgst")), _d(payload.get("sgst"))
            else:
                tax = _d(payload.get("tax"))
                cgst = (tax / 2).quantize(Decimal("0.01"))
                sgst = tax - cgst
            taxable = amount - cgst - sgst
            lines = [(party, amount), (sales, -taxable),
                     (payload.get("cgst_ledger") or "Output CGST", -cgst),
                     (payload.get("sgst_ledger") or "Output SGST", -sgst)]
        else:
            lines = [(party, amount), (sales, -amount)]
        return build_voucher(voucher_type="Sales", reference=ref, voucher_date=vdate, company_name=company_name,
                             party_ledger=party, lines=lines,
                             narration=f"WearVerse {payload.get('channel', 'shop')} bill {payload.get('bill_no', ref)}")
    if event_type == "receipt_voucher":
        cash = payload.get("cash_ledger") or "Cash"
        return build_voucher(voucher_type="Receipt", reference=ref, voucher_date=vdate, company_name=company_name,
                             party_ledger=party, lines=[(cash, amount), (party, -amount)],
                             narration=f"Payment received ({payload.get('mode', '')})")
    if event_type == "credit_note":
        sales = payload.get("sales_ledger") or "Sales"
        return build_voucher(voucher_type="Credit Note", reference=ref, voucher_date=vdate, company_name=company_name,
                             party_ledger=party, lines=[(sales, amount), (party, -amount)],
                             narration=f"Return against {payload.get('against', '')}")
    if event_type == "purchase_voucher":
        tax = _d(payload.get("tax"))
        cgst = (tax / 2).quantize(Decimal("0.01"))
        lines = [(payload.get("purchase_ledger") or "Purchase", _d(payload.get("taxable")) or amount - tax),
                 (payload.get("cgst_ledger") or "Input CGST", cgst),
                 (payload.get("sgst_ledger") or "Input SGST", tax - cgst), (party, -amount)]
        return build_voucher(voucher_type="Purchase", reference=ref, voucher_date=vdate, company_name=company_name,
                             party_ledger=party, lines=lines,
                             narration=f"Supplier bill {payload.get('supplier_bill_no', '')}")
    if event_type == "journal_voucher":
        return build_voucher(voucher_type="Journal", reference=ref, voucher_date=vdate, company_name=company_name,
                             party_ledger=None,
                             lines=[(payload["debit_ledger"], amount), (payload["credit_ledger"], -amount)],
                             narration=payload.get("narration", ""))
    raise ValueError(f"Unsupported Tally event type: {event_type}")
