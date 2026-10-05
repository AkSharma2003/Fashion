"""Tally bridge agent (skeleton).

Loop: ask the cloud for pending work, hand it to Tally, report the result.
The Tally part (build XML, post, read back) is intentionally not written yet: it depends on the
installed Tally version (see README).
"""
import time
from pathlib import Path

import requests
import yaml


def load_config() -> dict:
    path = Path(__file__).resolve().parent.parent / "config" / "tally-bridge.local.yaml"
    if not path.exists():
        path = path.with_name("config.example.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def post_to_tally(item: dict, cfg: dict) -> tuple[bool, str]:
    """TODO: build the voucher XML for item['payload'] and post it to Tally. Return (ok, message)."""
    return False, "not implemented"


def run() -> None:
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    base = cfg["api_base_url"]
    while True:
        try:
            resp = requests.get(f"{base}/tally/outbox/pending", headers=headers, timeout=20)
            resp.raise_for_status()
            for item in resp.json().get("data", []):
                ok, message = post_to_tally(item, cfg)
                requests.post(
                    f"{base}/tally/outbox/{item['id']}/result",
                    json={"ok": ok, "message": message},
                    headers=headers,
                    timeout=20,
                )
        except requests.RequestException as exc:
            print(f"cloud unreachable, will retry: {exc}")
        time.sleep(cfg.get("poll_seconds", 15))


if __name__ == "__main__":
    run()
