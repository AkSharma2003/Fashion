"""Read new or changed vouchers from Tally (Mode A import) using Tally's ALTERID change counter.

[Verify for the latest TallyPrime in Sprint 0: field names and the inventory list tag.]
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

WANTED_TYPES = {"sales", "credit note", "purchase", "receipt"}


def vouchers_request(company_name: str, last_alter_id: int) -> str:
    return f"""<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
<TYPE>Collection</TYPE><ID>WVChangedVouchers</ID></HEADER><BODY><DESC><STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVCURRENTCOMPANY>{escape(company_name)}</SVCURRENTCOMPANY>
</STATICVARIABLES><TDL><TDLMESSAGE>
<COLLECTION NAME="WVChangedVouchers" ISMODIFY="No"><TYPE>Voucher</TYPE>
<FETCH>GUID, ALTERID, DATE, VOUCHERTYPENAME, VOUCHERNUMBER, REFERENCE, PARTYLEDGERNAME, AMOUNT, ALLINVENTORYENTRIES.LIST, ALLLEDGERENTRIES.LIST</FETCH>
<FILTER>WVNewerThanLast</FILTER></COLLECTION>
<SYSTEM TYPE="Formulae" NAME="WVNewerThanLast">$AlterID &gt; {int(last_alter_id)}</SYSTEM>
</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>"""


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def _amount(value: str) -> str:
    try:
        return f"{abs(float(value.replace(',', ''))):.2f}"
    except ValueError:
        return "0.00"


def _qty(value: str) -> int:
    number = value.strip().split(" ")[0] if value else "0"
    try:
        return int(abs(float(number)))
    except ValueError:
        return 0


def parse_vouchers(xml_text: str) -> tuple[list[dict], int]:
    """Returns (records for /tally/inbox, highest ALTERID seen)."""
    root = ET.fromstring(xml_text)
    records, max_alter = [], 0
    for v in root.iter("VOUCHER"):
        vtype = _text(v, "VOUCHERTYPENAME")
        alter_id = int(_text(v, "ALTERID") or 0)
        max_alter = max(max_alter, alter_id)
        if vtype.lower() not in WANTED_TYPES:
            continue
        raw_date = _text(v, "DATE")
        items = []
        for tag in ("ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"):
            for inv in v.iter(tag):
                items.append({"stock_item": _text(inv, "STOCKITEMNAME"),
                              "qty": _qty(_text(inv, "BILLEDQTY") or _text(inv, "ACTUALQTY")),
                              "amount": _amount(_text(inv, "AMOUNT"))})
        party = _text(v, "PARTYLEDGERNAME")
        amount = _text(v, "AMOUNT")
        if not amount:
            for led in v.iter("ALLLEDGERENTRIES.LIST"):
                if _text(led, "LEDGERNAME") == party:
                    amount = _text(led, "AMOUNT")
        records.append({
            "kind": "voucher", "guid": _text(v, "GUID") or v.get("REMOTEID", ""), "alter_id": alter_id,
            "voucher_type": vtype, "voucher_number": _text(v, "VOUCHERNUMBER"),
            "reference": _text(v, "REFERENCE"),
            "date": f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else None,
            "party_ledger": party, "amount": _amount(amount or "0"), "items": items,
        })
    return records, max_alter
