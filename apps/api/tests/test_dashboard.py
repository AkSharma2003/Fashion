"""Owner dashboard counts only what is still for sale, and shows what needs attention."""
from app.modules.catalog.models import Product
from app.modules.store.models import ContactMessage

from tests.wv_fixtures import auth, client, db, engine, make_user, make_variant  # noqa: F401


def test_low_stock_ignores_archived_and_lists_items(client, db):
    keep = make_variant(db, name="Last Piece Saree", qty=1)
    gone = make_variant(db, name="Archived Saree", qty=0)
    db.get(Product, gone.product_id).is_active = False
    db.add(ContactMessage(name="A", email="a@example.com", message="hello there"))
    db.commit()
    d = client.get("/api/v1/reports/dashboard", headers=auth(make_user(db, "Manager"))).json()["data"]
    names = [i["product"] for i in d["low_stock_items"]]
    assert "Last Piece Saree" in names and "Archived Saree" not in names
    assert d["low_stock_variants"] == 1 and d["new_messages"] == 1 and d["unpaid_orders"] == 0
    assert keep.sku in [i["sku"] for i in d["low_stock_items"]]
