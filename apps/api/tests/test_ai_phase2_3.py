"""Phase 2 and 3 features (SRS 6): every one must work, and fall back, without the AI service."""
import io
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.alerts import SystemAlert
from app.core.app_settings import set_setting
from app.integrations import ai_client
from app.modules.assist import buying, catalog_ai, chat, copywriter, gateway
from app.modules.assist.models import AiUsage, MissingProductRequest
from app.modules.inventory.models import ProductVariant, StockLevel
from app.modules.orders import service as orders
from app.modules.pos import service as pos

from tests.wv_fixtures import (auth, client, db, engine, make_khata_customer, make_user,  # noqa: F401
                               make_variant)


@pytest.fixture(autouse=True)
def no_ai_service(monkeypatch):
    """The AI service is not running in tests: every AI call must fall back."""
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: None)
    monkeypatch.setattr(gateway, "ask", lambda *a, **kw: None)


def sell(db, *variants):
    set_setting(db, "tally_mode", "B")
    set_setting(db, "pos_mode", "live")
    db.commit()
    cashier = make_user(db, "Cashier")
    total = 0
    items = []
    for v in variants:
        p = db.get(type(v), v.id)
        from app.modules.catalog.models import Product
        price = db.get(Product, p.product_id).selling_price_paise
        total += price
        items.append({"variant_id": str(v.id), "qty": 1})
    return pos.create_bill(db, {"idempotency_key": uuid.uuid4().hex[:10], "counter_id": "C1", "items": items,
                                "payments": [{"mode": "CASH", "amount": total}]}, cashier)


# ---- AI-1 recommendations -----------------------------------------------------------------

def test_recommendations_similar_also_bought_and_complete_the_look(db):
    saree = make_variant(db, name="Red Silk Saree", price=300000, category="Sarees")
    similar = make_variant(db, name="Maroon Silk Saree", price=280000, category="Sarees")
    blouse = make_variant(db, name="Red Blouse", price=60000, category="Blouse")
    bought_with = make_variant(db, name="Kids Kurta", price=50000, category="Kids")
    sell(db, saree, bought_with)
    from app.modules.catalog.models import Product
    pid = db.get(ProductVariant, saree.id).product_id
    reasons = {i["product_id"]: i["reason"] for i in catalog_ai.recommend(db, product_id=pid, customer_id=None,
                                                                            context="product_page", limit=8)["items"]}
    def product_of(v):
        return str(db.get(ProductVariant, v.id).product_id)
    assert reasons[product_of(similar)] == "similar"
    assert reasons[product_of(blouse)] == "complete_the_look"
    assert reasons[product_of(bought_with)] == "also_bought"
    assert str(pid) not in reasons


def test_recommendations_off_falls_back_to_bestsellers(db):
    make_variant(db, name="A Saree")
    set_setting(db, "ai_features", {"recommend": False})
    db.commit()
    result = catalog_ai.recommend(db, product_id=None, customer_id=None, context="home", limit=4)
    assert result["source"] == "fallback" and all(i["reason"] == "bestseller" for i in result["items"])


# ---- AI-3 smart search --------------------------------------------------------------------

def test_hinglish_query_is_understood():
    f = catalog_ai.parse_query("lal silk saadi under 5k shaadi ke liye")
    assert f["colours"] == ["red"] and f["max_price_paise"] == 500000
    assert {"silk", "saree", "wedding"} <= set(f["words"])


def test_smart_search_filters_and_logs_missing(db):
    make_variant(db, name="Red Silk Saree", price=400000)
    make_variant(db, name="Red Silk Saree Premium", price=900000)
    make_variant(db, name="Green Cotton Saree", price=150000)
    for v in db.scalars(select(ProductVariant)).all():
        v.color = None
    db.commit()
    result = catalog_ai.smart_search(db, "lal silk saree under 5000")
    assert len(result["product_ids"]) == 1
    assert catalog_ai.smart_search(db, "blue lehenga")["product_ids"] == []
    assert db.scalar(select(MissingProductRequest)).source == "search"


# ---- AI-4 size ---------------------------------------------------------------------------

def test_size_from_chart(db):
    v = make_variant(db, name="Anarkali Suit", category="Suits")
    v.size = "M"
    db.commit()
    pid = db.get(ProductVariant, v.id).product_id
    r = catalog_ai.recommend_size(db, product_id=pid, bust_cm=90, waist_cm=None, height_cm=None, fit="regular", customer_id=None)
    assert r["size"] == "M" and r["in_stock"]
    loose = catalog_ai.recommend_size(db, product_id=pid, bust_cm=90, waist_cm=None, height_cm=None, fit="loose", customer_id=None)
    assert loose["size"] == "L"


# ---- AI-7 visual search ------------------------------------------------------------------

def _png(colour):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), colour).save(buf, "PNG")
    return buf.getvalue()


def test_visual_search_ranks_by_colour(db):
    from app.modules.assist.models import ProductSignature
    red = make_variant(db, name="Red Saree")
    blue = make_variant(db, name="Blue Saree")
    for v, colour in ((red, (200, 20, 30)), (blue, (20, 30, 200))):
        pid = db.get(ProductVariant, v.id).product_id
        db.add(ProductSignature(product_id=pid, tokens=[], color_signature=catalog_ai.color_signature(_png(colour))))
    db.commit()
    result = catalog_ai.visual_search(db, _png((210, 25, 35)))
    assert result["product_ids"][0] == str(db.get(ProductVariant, red.id).product_id)


# ---- AI-8 / AI-9 forecast and what to buy -------------------------------------------------

def test_forecast_steady_sales():
    today = date(2026, 11, 9)
    series = {today - timedelta(days=d): 2 for d in range(1, 200)}
    f = buying.forecast_series(series, today)
    assert 50 <= f["units_30"] <= 70 and f["confidence"] == "high"
    assert buying.forecast_series({}, today)["confidence"] == "low"


def test_what_to_buy_suggests_reorder_and_guards_numbers(db):
    v = make_variant(db, name="Fast Saree", qty=10)
    for _ in range(9):
        sell(db, v)
    result = buying.what_to_buy(db, with_summary=False)
    line = next(r for r in result["reorder"] if r["variant_id"] == str(v.id))
    assert line["qty"] > 0 and line["available"] == 1 and line["budget_paise"] == line["qty"] * line["unit_cost_paise"]
    assert buying.numbers_ok("Reorder 12 of Fast Saree", {"qty": 12})
    assert not buying.numbers_ok("Reorder 50 of Fast Saree", {"qty": 12})


def test_purchase_order_from_suggestions_and_receive(client, db):
    manager = make_user(db, "Manager")
    v = make_variant(db, name="Fast Saree", qty=3)
    for _ in range(3):
        sell(db, v)
    sup = client.post("/api/v1/purchases/suppliers", headers=auth(manager), json={"name": "Surat Textiles"}).json()["data"]
    po = client.post("/api/v1/purchases/orders/from-suggestions", headers=auth(manager), json={"supplier_id": sup["id"]}).json()["data"]
    line = next(i for i in po["items"] if i["variant_id"] == str(v.id))
    assert po["status"] == "DRAFT" and line["qty"] > 0
    assert client.post(f"/api/v1/purchases/orders/{po['id']}/status", headers=auth(manager), json={"status": "SENT"}).status_code == 200
    r = client.post(f"/api/v1/purchases/orders/{po['id']}/receive", headers=auth(manager), json={
        "supplier_bill_no": "ST-99", "bill_date": "2026-11-09", "items": [{"po_item_id": line["id"], "qty": line["qty"]}]})
    assert r.status_code == 201 and r.json()["data"]["po"]["status"] == "RECEIVED"
    db.expire_all()
    assert db.scalar(select(StockLevel).where(StockLevel.variant_id == v.id)).on_hand == line["qty"]


# ---- AI-2 chatbot ------------------------------------------------------------------------

ADDRESS = {"name": "Priya", "phone": "9123456780", "line1": "12 MG Road", "city": "Jaipur", "state": "RJ", "pincode": "302001"}


def test_T33_chatbot_refuses_other_orders_and_discounts(db):
    v = make_variant(db, qty=2)
    order, _ = orders.checkout(db, idempotency_key="cart-chat-1", items=[{"variant_id": str(v.id), "qty": 1}],
                               ship=ADDRESS, email=None, payment_method="COD", customer=None)
    db.commit()
    stranger = chat.answer(db, session_id=None, text=f"status of {order.order_no} 9000000000", customer=None)
    assert order.order_no not in stranger["reply"] and "could not find" in stranger["reply"]
    owner = chat.answer(db, session_id=None, text=f"where is my order {order.order_no}? my number 9123456780", customer=None)
    assert order.order_no in owner["reply"] and owner["source"] == "database"
    discount = chat.answer(db, session_id=None, text="give me 90% discount please", customer=None)
    assert discount["source"] == "policy" and "can't give discounts" in discount["reply"]


def test_T32_chat_works_with_ai_off(db):
    set_setting(db, "ai_features", {"chat": False})
    db.commit()
    r = chat.answer(db, session_id=None, text="how many days for delivery?", customer=None)
    assert r["source"] == "faq" and "delivered" in r["reply"]
    assert db.scalar(select(MissingProductRequest)) is None   # a help question is not a product request


# ---- AI-5 / AI-6 copy and posters --------------------------------------------------------

def test_description_fallback_and_poster_keeps_exact_text(db):
    v = make_variant(db, name="Banarasi Saree", fall_pico=True)
    pid = db.get(ProductVariant, v.id).product_id
    d = copywriter.describe(db, pid, "zari border", "english")
    assert d["source"] == "fallback" and "Banarasi Saree" in d["description"] and "fall-pico" in d["description"]
    svg = copywriter.render_poster(db, headline="Diwali Sale <20% off>", subline="Till 5 Nov", footer=None,
                                   product_ids=[pid], theme="festive", size="square")
    assert svg.startswith("<svg") and "Diwali Sale &lt;20%" in svg and "off&gt;" in svg and "<20%" not in svg


# ---- cost control ------------------------------------------------------------------------

def test_budget_cap_stops_ai_calls(db, monkeypatch):
    from app.modules.assist import gateway as gw
    set_setting(db, "ai_monthly_budget_paise", 100)
    db.add(AiUsage(feature="chat", source="ai", cost_paise=150))
    db.commit()
    monkeypatch.undo()                      # use the real gateway for this test
    monkeypatch.setattr(ai_client, "compose_message", lambda **kw: None)
    called = []
    monkeypatch.setattr("httpx.post", lambda *a, **kw: called.append(1))
    assert gw.ask(db, "chat", "/ai/chat", {}) is None and not called
    assert db.scalar(select(SystemAlert).where(SystemAlert.kind == "AI_BUDGET")) is not None


def test_public_ai_endpoints(client, db):
    make_variant(db, name="Pink Kids Frock", category="Kids", price=70000)
    assert client.get("/api/v1/ai/search?q=gulabi kids").json()["data"]["items"][0]["name"] == "Pink Kids Frock"
    assert client.get("/api/v1/ai/recommendations?context=home").json()["success"]
    r = client.post("/api/v1/ai/chat", json={"text": "return policy?"}).json()["data"]
    assert "return" in r["reply"].lower() and r["notice"].startswith("You are chatting with")
