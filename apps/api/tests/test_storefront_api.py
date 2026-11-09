"""Public website API used by the storefront pages: category lists, product detail, contact form."""
from tests.wv_fixtures import auth, client, db, engine, make_user, make_variant  # noqa: F401


def test_category_list_and_single_variant_card(client, db):
    variant = make_variant(db, name="Silk Saree", price=150000, qty=3)
    items = client.get("/api/v1/store/products", params={"category": variant_category(db, variant)}).json()["data"]["items"]
    card = next(i for i in items if i["name"] == "Silk Saree")
    assert card["in_stock"] is True
    assert card["single_variant"]["id"] == str(variant.id) and card["single_variant"]["available"] == 3


def variant_category(db, variant):
    from app.modules.catalog.models import Product
    return db.get(Product, variant.product_id).category


def test_product_detail_has_variants_with_stock(client, db):
    variant = make_variant(db, qty=2)
    data = client.get(f"/api/v1/store/products/{variant.product_id}").json()["data"]
    assert data["variants"][0]["available"] == 2 and data["variants"][0]["price_paise"] > 0


def test_contact_message_reaches_staff(client, db):
    r = client.post("/api/v1/store/contact", json={"name": "Meena", "email": "meena@example.com", "message": "Do you have red silk sarees?"})
    assert r.status_code == 200
    online = make_user(db, "OnlineStaff")
    msgs = client.get("/api/v1/store/contact-messages", headers=auth(online)).json()["data"]
    assert msgs[0]["name"] == "Meena" and msgs[0]["status"] == "NEW"
    done = client.patch(f"/api/v1/store/contact-messages/{msgs[0]['id']}", json={"status": "DONE"}, headers=auth(online))
    assert done.json()["data"]["status"] == "DONE"


def test_contact_messages_need_staff(client, db):
    assert client.get("/api/v1/store/contact-messages").status_code in (401, 403)
    cashier = make_user(db, "Cashier")
    assert client.get("/api/v1/store/contact-messages", headers=auth(cashier)).status_code == 403
