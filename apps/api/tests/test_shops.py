"""Three shops (Sethi Saree Sansar, Sethi Suit, Sethi Kids): own stock, own counters and bills, staff tied to a shop."""
from app.core.app_settings import set_setting
from app.integrations import ai_client
from app.modules.inventory import stock
from app.modules.inventory.models import StockLevel
from app.modules.orders.models import OrderItem
from app.modules.pos.models import Counter
from app.modules.shops.service import ensure_default_shops

import pytest

from tests.wv_fixtures import auth, client, db, engine, make_user, make_variant  # noqa: F401


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: None)


def setup(db):
    shops = {s.code: s for s in ensure_default_shops(db)}
    for code, sc in (("SSS-C1", "SSS"), ("SS-C1", "SS"), ("SK-C1", "SK")):
        db.add(Counter(code=code, name=code, shop_id=shops[sc].id))
    set_setting(db, "tally_mode", "B")
    set_setting(db, "pos_mode", "live")
    db.commit()
    return shops


def level(db, variant, shop):
    return db.query(StockLevel).filter_by(variant_id=variant.id, shop_id=shop.id).one_or_none()


def bill(client, user, counter, variant, key):
    return client.post("/api/v1/pos/bills", headers=auth(user), json={
        "idempotency_key": key, "counter_id": counter, "items": [{"variant_id": str(variant.id), "qty": 1}],
        "payments": [{"mode": "CASH", "amount": 150000}]})


def test_bill_at_sethi_kids_uses_its_own_stock_and_series(client, db):
    shops = setup(db)
    v = make_variant(db, qty=0)
    stock.move(db, v.id, 2, "opening", source="adjustment", shop_id=shops["SSS"].id)
    stock.move(db, v.id, 3, "opening", source="adjustment", shop_id=shops["SK"].id)
    db.commit()
    r = bill(client, make_user(db, "Cashier"), "SK-C1", v, "key-k1")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["bill_no"].startswith("SK-C1-")
    db.expire_all()
    assert level(db, v, shops["SK"]).on_hand == 2 and level(db, v, shops["SSS"]).on_hand == 2


def test_cashier_of_one_shop_cannot_bill_or_see_another_shop(client, db):
    shops = setup(db)
    v = make_variant(db, qty=5)
    suit_cashier = make_user(db, "Cashier")
    suit_cashier.shop_id = shops["SS"].id
    db.commit()
    assert bill(client, suit_cashier, "SSS-C1", v, "key-x1").status_code == 403
    counters = client.get("/api/v1/pos/counters", headers=auth(suit_cashier)).json()["data"]
    assert [c["code"] for c in counters] == ["SS-C1"]
    main_bill = bill(client, make_user(db, "Cashier"), "SSS-C1", v, "key-x2").json()["data"]
    assert client.get(f"/api/v1/pos/bills/{main_bill['bill_id'] if 'bill_id' in main_bill else main_bill['id']}",
                      headers=auth(suit_cashier)).status_code == 403
    assert client.get("/api/v1/pos/bills", headers=auth(suit_cashier)).json()["data"] == []


def test_website_sells_from_any_shop_and_holds_stock_where_it_is(client, db):
    shops = setup(db)
    v = make_variant(db, qty=0, category="Kids")
    stock.move(db, v.id, 1, "opening", source="adjustment", shop_id=shops["SK"].id)
    db.commit()
    card = client.get(f"/api/v1/store/products/{v.product_id}").json()["data"]
    assert card["in_stock"] is True and card["variants"][0]["available"] == 1
    r = client.post("/api/v1/store/checkout", json={
        "idempotency_key": "web-shop-1", "payment_method": "COD", "items": [{"variant_id": str(v.id), "qty": 1}],
        "address": {"name": "Asha", "phone": "9811111111", "line1": "12 Rose Apts", "city": "Vadodara",
                    "state": "Gujarat", "pincode": "390001"}})
    assert r.status_code == 200, r.text
    item = db.query(OrderItem).one()
    assert item.shop_id == shops["SK"].id
    db.expire_all()
    assert level(db, v, shops["SK"]).on_hand == 0          # COD confirmed: taken from Sethi Kids


def test_stock_adjustment_goes_to_the_picked_shop_and_lists_per_shop(client, db):
    shops = setup(db)
    v = make_variant(db, qty=0)
    manager = make_user(db, "Manager")
    h = {**auth(manager), "X-Shop-Id": str(shops["SS"].id)}
    r = client.post("/api/v1/inventory/stock/adjustments", headers=h,
                    json={"variant_id": str(v.id), "quantity_delta": 4, "reason": "new stock"})
    assert r.status_code == 201, r.text
    rows = client.get("/api/v1/inventory/stock", headers=h).json()
    assert [(x["shop"], x["on_hand"]) for x in rows if x["variant_id"] == str(v.id)] == [("SS", 4)]


def test_dashboard_for_one_shop_counts_only_its_bills(client, db):
    shops = setup(db)
    v = make_variant(db, qty=5)
    cashier = make_user(db, "Cashier")
    bill(client, cashier, "SSS-C1", v, "key-d1")
    bill(client, cashier, "SK-C1", v, "key-d2")
    owner = make_user(db, "Owner")
    all_shops = client.get("/api/v1/reports/dashboard", headers=auth(owner)).json()["data"]
    kids = client.get("/api/v1/reports/dashboard", headers={**auth(owner), "X-Shop-Id": str(shops["SK"].id)}).json()["data"]
    assert all_shops["today"]["bills"] == 2 and kids["today"]["bills"] == 1


def test_shops_list_and_owner_can_set_gstin(client, db):
    shops = setup(db)
    owner = make_user(db, "Owner")
    names = [s["name"] for s in client.get("/api/v1/shops", headers=auth(owner)).json()["data"]]
    assert names[0] == "Sethi Saree Sansar" and set(names) == {"Sethi Saree Sansar", "Sethi Suit", "Sethi Kids"}
    r = client.patch(f"/api/v1/shops/{shops['SS'].id}", headers=auth(owner), json={"gstin": "24ABCDE1234F1Z5", "state_code": "24"})
    assert r.json()["data"]["gstin"] == "24ABCDE1234F1Z5"
    assert client.patch(f"/api/v1/shops/{shops['SS'].id}", headers=auth(make_user(db, "Manager")), json={"name": "X"}).status_code == 403
