"""Back-office product list and delete: real delete only without history, otherwise archive."""
from app.modules.catalog.models import Product
from app.modules.inventory.models import ProductVariant

from tests.wv_fixtures import auth, client, db, engine, make_user, make_variant  # noqa: F401


def test_list_has_stock_colours_and_archived_toggle(client, db):
    v = make_variant(db, name="Kanjeevaram", qty=4)
    row = next(r for r in client.get("/api/v1/catalog/").json() if r["id"] == str(v.product_id))
    assert row["stock_on_hand"] == 4 and row["variant_count"] == 1 and row["colors"] == ["Red"]
    db.get(Product, v.product_id).is_active = False
    db.commit()
    assert all(r["id"] != str(v.product_id) for r in client.get("/api/v1/catalog/").json())
    assert any(r["id"] == str(v.product_id) for r in client.get("/api/v1/catalog/?include_inactive=true").json())


def test_product_without_history_is_deleted(client, db):
    v = make_variant(db, qty=0)              # no opening stock, never sold
    pid, vid = v.product_id, v.id
    r = client.delete(f"/api/v1/catalog/{pid}/permanent", headers=auth(make_user(db, "Manager"))).json()
    assert r["deleted"] is True
    db.expire_all()
    assert db.get(Product, pid) is None and db.get(ProductVariant, vid) is None


def test_product_with_stock_history_is_archived_not_deleted(client, db):
    v = make_variant(db, qty=3)              # opening stock movement = history
    r = client.delete(f"/api/v1/catalog/{v.product_id}/permanent", headers=auth(make_user(db, "Manager"))).json()
    assert r["deleted"] is False and r["archived"] is True
    db.expire_all()
    assert db.get(Product, v.product_id).is_active is False


def test_variant_delete_and_role_check(client, db):
    v = make_variant(db, qty=0)
    assert client.delete(f"/api/v1/catalog/{v.product_id}/permanent", headers=auth(make_user(db, "Cashier"))).status_code == 403
    r = client.delete(f"/api/v1/catalog/{v.product_id}/variants/{v.id}/permanent", headers=auth(make_user(db, "Manager"))).json()
    assert r["deleted"] is True
