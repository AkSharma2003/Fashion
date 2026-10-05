"""Create a backend module with the standard pattern.

Usage:  python scripts/new_module.py khata
Creates apps/api/app/modules/khata/{__init__,router,schemas,service,repository,models,events}.py
Then add the module name to MODULES in apps/api/app/modules/__init__.py.
"""
import sys
from pathlib import Path

FILES = {
    "__init__.py": "",
    "router.py": "from fastapi import APIRouter\n\nrouter = APIRouter()\n",
    "schemas.py": '"""Request and response validation (Pydantic)."""\n',
    "service.py": '"""Business logic. Writes to money, stock, ledgers go through here, inside one transaction."""\n',
    "repository.py": '"""Database operations only. No business rules here."""\n',
    "models.py": '"""SQLAlchemy models. Money columns are integers in paise."""\n',
    "events.py": '"""Domain and integration events (for the outbox)."""\n',
}

def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/new_module.py <module_name>")
    name = sys.argv[1].strip().lower().replace("-", "_")
    target = Path(__file__).resolve().parent.parent / "apps" / "api" / "app" / "modules" / name
    if target.exists():
        sys.exit(f"module already exists: {target}")
    target.mkdir(parents=True)
    for filename, content in FILES.items():
        (target / filename).write_text(content, encoding="utf-8")
    print(f"created {target}")
    print(f"next: add '{name}' to MODULES in apps/api/app/modules/__init__.py")

if __name__ == "__main__":
    main()
