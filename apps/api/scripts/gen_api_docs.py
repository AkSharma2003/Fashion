"""Write docs/api/endpoints.md from the API's OpenAPI spec.

    cd apps/api && python -m scripts.gen_api_docs
"""
from collections import defaultdict
from pathlib import Path

from app.main import app

OUT = Path(__file__).resolve().parents[3] / "docs" / "api" / "endpoints.md"
ORDER = ["get", "post", "put", "patch", "delete"]


def main() -> None:
    groups: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for path, ops in app.openapi()["paths"].items():
        for method, op in ops.items():
            tag = (op.get("tags") or ["other"])[0]
            groups[tag].append((path, method, op.get("summary", "")))
    lines = [
        "# Endpoint list",
        "",
        "Generated from the API by `python -m scripts.gen_api_docs` (in `apps/api`). Do not edit by hand.",
        "Request and response fields: `http://localhost:8000/docs`. Conventions: [README.md](README.md).",
        "",
    ]
    total = 0
    for tag in sorted(groups):
        rows = sorted(groups[tag], key=lambda r: (r[0], ORDER.index(r[1]) if r[1] in ORDER else 9))
        total += len(rows)
        lines += [f"## {tag}", "", "| Method | Path | What it does |", "|---|---|---|"]
        lines += [f"| {m.upper()} | `{p}` | {s} |" for p, m, s in rows]
        lines.append("")
    lines[2] += f" {total} operations."
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT} ({total} operations)")


if __name__ == "__main__":
    main()
