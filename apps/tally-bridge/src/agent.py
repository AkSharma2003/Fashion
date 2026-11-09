"""WearVerse <-> Tally bridge agent. Outbound HTTPS only; Tally's port is never opened to the internet."""

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

from tally_reader import parse_vouchers, vouchers_request
from voucher_builder import (
    parse_import_response,
    voucher_from_event
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


def _client(cfg: dict) -> TallyClient:
    return TallyClient(host=str(cfg["tally_host"]), port=int(cfg.get("tally_port", 9000)),
                       timeout=int(cfg.get("tally_timeout_seconds", 10)))


def post_to_tally(item: dict, cfg: dict) -> tuple[bool, str]:
    payload = item.get("payload") or {}
    try:
        xml_data = voucher_from_event(str(item.get("event_type")), payload, str(cfg["company_name"]))
        return parse_import_response(_client(cfg).post_xml(xml_data))
    except (KeyError, TypeError, ValueError, TallyError) as exc:
        return False, str(exc)


def read_from_tally(cfg: dict, base: str, headers: dict, timeout: int) -> None:
    """Mode A: send vouchers made or changed in Tally to WearVerse (/tally/inbox)."""
    beat = requests.post(f"{base}/tally/heartbeat", json={"agent": "wearverse-tally-bridge"},
                         headers=headers, timeout=timeout)
    beat.raise_for_status()
    last = int(beat.json().get("last_alter_id") or 0)
    xml_text = _client(cfg).post_xml(vouchers_request(str(cfg["company_name"]), last))
    records, max_alter = parse_vouchers(xml_text)
    if not records and max_alter <= last:
        return
    for start in range(0, max(len(records), 1), 200):
        chunk = records[start:start + 200]
        result = requests.post(f"{base}/tally/inbox",
                               json={"records": chunk, "last_alter_id": max_alter if start + 200 >= len(records) else None},
                               headers=headers, timeout=timeout)
        result.raise_for_status()
        print(f"inbox: {result.json()}")


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

    if cfg.get("read_from_tally", True):
        try:
            read_from_tally(cfg, base, headers, int(cfg.get("api_timeout_seconds", 20)))
        except (TallyError, ValueError) as exc:
            print(f"reading from Tally failed, will retry: {exc}")


def run() -> None:

    cfg = load_config()

    poll_seconds = int(
        cfg.get(
            "poll_seconds",
            15
        )
    )

    print(
        "WearVerse Tally Bridge started: "
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
        description="WearVerse Tally bridge"
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