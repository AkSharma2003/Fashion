from importlib import import_module

# Add a module name here after creating it with scripts/new_module.py
MODULES = ["auth", "catalog", "inventory", "customers", "pos", "khata", "payments", "orders", "shipping", "purchasing", "employees", "fall_pico", "notifications", "tally", "analytics", "settings"]

routers = [(name, import_module(f"app.modules.{name}.router").router) for name in MODULES]
