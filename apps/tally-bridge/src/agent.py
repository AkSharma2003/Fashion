"""FashionOS -> Tally bridge agent."""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path

import requests
import yaml

from tally_client import (
    TallyClient,
    TallyError
)

from voucher_builder import (
    build_sales_voucher,
    parse_import_response
)


ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:

    path = (
        ROOT
        / "config"
        / "tally-bridge.local.yaml"
    )

    if not path.exists():

        path = (
            ROOT
            / "config"
            / "config.example.yaml"
        )

    return (
        yaml.safe_load(
            path.read_text(
                encoding="utf-8"
            )
        )
        or {}
    )


def _api_headers(
    cfg: dict
) -> dict:

    return {
        "X-Tally-Agent-Key":
        cfg["api_key"]
    }


def post_to_tally(
    item: dict,
    cfg: dict
) -> tuple[bool, str]:

    payload = item.get("payload") or {}

    event_type = item.get(
        "event_type"
    )

    if event_type != "sales_voucher":

        return (
            False,
            f"Unsupported Tally event type: "
            f"{event_type}"
        )

    try:

        xml_data = build_sales_voucher(

            reference=str(
                payload["reference"]
            ),

            voucher_date=payload.get(
                "voucher_date",
                date.today()
            ),

            customer_name=str(
                payload["customer_name"]
            ),

            amount=payload["amount"],

            company_name=str(
                cfg["company_name"]
            ),

            party_ledger=payload.get(
                "party_ledger"
            ),

            sales_ledger=str(
                payload.get(
                    "sales_ledger",
                    cfg.get(
                        "sales_ledger",
                        "Sales"
                    )
                )
            )
        )

        response = TallyClient(

            host=str(
                cfg["tally_host"]
            ),

            port=int(
                cfg.get(
                    "tally_port",
                    9000
                )
            ),

            timeout=int(
                cfg.get(
                    "tally_timeout_seconds",
                    10
                )
            )

        ).post_xml(xml_data)

        return parse_import_response(
            response
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        TallyError
    ) as exc:

        return False, str(exc)


def test_tally(
    cfg: dict
) -> int:

    client = TallyClient(

        host=str(
            cfg["tally_host"]
        ),

        port=int(
            cfg.get(
                "tally_port",
                9000
            )
        ),

        timeout=int(
            cfg.get(
                "tally_timeout_seconds",
                10
            )
        )
    )

    ok, message = (
        client.test_connection()
    )

    print(message)

    return 0 if ok else 1


def run_once(
    cfg: dict
) -> None:

    base = str(
        cfg["api_base_url"]
    ).rstrip("/")

    headers = _api_headers(
        cfg
    )

    response = requests.get(

        f"{base}/tally/outbox/pending",

        headers=headers,

        timeout=int(
            cfg.get(
                "api_timeout_seconds",
                20
            )
        )
    )

    response.raise_for_status()

    for item in response.json().get(
        "data",
        []
    ):

        ok, message = post_to_tally(
            item,
            cfg
        )

        result = requests.post(

            f"{base}/tally/outbox/"
            f"{item['id']}/result",

            json={
                "ok": ok,
                "message": message
            },

            headers=headers,

            timeout=int(
                cfg.get(
                    "api_timeout_seconds",
                    20
                )
            )
        )

        result.raise_for_status()

        print(
            f"{item['id']}: "
            f"{'OK' if ok else 'FAILED'} "
            f"- {message}"
        )


def run() -> None:

    cfg = load_config()

    poll_seconds = int(
        cfg.get(
            "poll_seconds",
            15
        )
    )

    print(
        "FashionOS Tally Bridge started: "
        f"Tally={cfg['tally_host']}:"
        f"{cfg.get('tally_port', 9000)} "
        f"poll={poll_seconds}s"
    )

    while True:

        try:

            run_once(cfg)

        except requests.RequestException as exc:

            print(
                "cloud/API unavailable, "
                f"retrying: {exc}"
            )

        except Exception as exc:

            print(
                f"bridge error, retrying: {exc}"
            )

        time.sleep(
            poll_seconds
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="FashionOS Tally bridge"
    )

    parser.add_argument(
        "--test-tally",
        action="store_true",
        help=(
            "test local Tally HTTP/XML "
            "access and exit"
        )
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "process pending outbox once "
            "and exit"
        )
    )

    args = parser.parse_args()

    cfg = load_config()

    if args.test_tally:

        raise SystemExit(
            test_tally(cfg)
        )

    if args.once:

        run_once(cfg)

        return

    run()


if __name__ == "__main__":
    main()