"""Build Tally XML vouchers from normalized FashionOS payloads."""

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