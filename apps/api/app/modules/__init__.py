from importlib import import_module

# Add a module name here after creating it with scripts/new_module.py
MODULES = [
    "auth", "catalog", "inventory", "customers", "pos", "khata", "payments", "pay", "webhooks", "store",
    "orders", "shipping", "purchasing", "employees", "payroll", "fall_pico", "notifications", "tally",
    "analytics", "reports", "settings", "internal", "assist", "shops",
]

# URL prefix under /api/v1 when it differs from the module name (SRS 8.3 paths).
PREFIXES = {
    "fall_pico": "fp",
    "notifications": "messages",
    "purchasing": "purchases",
    "assist": "ai",
}

routers = [
    (PREFIXES.get(name, name.replace("_", "-")), import_module(f"app.modules.{name}.router").router)
    for name in MODULES
]
