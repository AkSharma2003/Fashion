"""Customer's own account: profile, photo, address book (default address rules, ownership)."""
from io import BytesIO

from PIL import Image

from app.core.security import create_customer_token
from app.modules.customers.models import Customer

from tests.wv_fixtures import client, db, engine  # noqa: F401

ADDR = {"name": "Asha Verma", "phone": "9811111111", "line1": "12, Rose Apartments", "line2": "MG Road",
        "city": "Vadodara", "state": "Gujarat", "pincode": "390001", "kind": "HOME"}


def _login(db, phone="9811111111", email="asha@example.com"):
    c = Customer(full_name="Asha Verma", phone_number=phone, email=email, is_active=True)
    db.add(c)
    db.commit()
    return {"Authorization": f"Bearer {create_customer_token(str(c.id))}"}


def test_profile_and_name_change(client, db):
    h = _login(db)
    me = client.get("/api/v1/store/me", headers=h).json()["data"]
    assert me["full_name"] == "Asha Verma" and me["email"] == "asha@example.com" and me["profile_photo_url"] is None
    me = client.patch("/api/v1/store/me", json={"full_name": "Asha V."}, headers=h).json()["data"]
    assert me["full_name"] == "Asha V."


def test_profile_needs_login(client, db):
    assert client.get("/api/v1/store/me").status_code == 401


def test_first_address_is_default_and_default_moves(client, db):
    h = _login(db)
    first = client.post("/api/v1/store/me/addresses", json=ADDR, headers=h).json()["data"]
    assert first["is_default"] is True and first["line2"] == "MG Road"
    second = client.post("/api/v1/store/me/addresses", json={**ADDR, "kind": "WORK", "line2": ""}, headers=h).json()["data"]
    assert second["is_default"] is False and second["line2"] is None
    client.post(f"/api/v1/store/me/addresses/{second['id']}/default", headers=h)
    rows = client.get("/api/v1/store/me/addresses", headers=h).json()["data"]
    assert [r["is_default"] for r in rows] == [True, False] and rows[0]["id"] == second["id"]
    # Deleting the default makes the other one default.
    client.delete(f"/api/v1/store/me/addresses/{second['id']}", headers=h)
    rows = client.get("/api/v1/store/me/addresses", headers=h).json()["data"]
    assert len(rows) == 1 and rows[0]["is_default"] is True


def test_cannot_touch_someone_elses_address(client, db):
    mine = client.post("/api/v1/store/me/addresses", json=ADDR, headers=_login(db)).json()["data"]
    other = _login(db, phone="9822222222", email="b@example.com")
    assert client.patch(f"/api/v1/store/me/addresses/{mine['id']}", json=ADDR, headers=other).status_code == 404
    assert client.delete(f"/api/v1/store/me/addresses/{mine['id']}", headers=other).status_code == 404


def test_bad_pincode_rejected(client, db):
    r = client.post("/api/v1/store/me/addresses", json={**ADDR, "pincode": "12345"}, headers=_login(db))
    assert r.status_code == 422


def test_photo_upload_is_resized(client, db, tmp_path, monkeypatch):
    from app.core.config import settings
    from app.modules.store import account
    monkeypatch.setattr(account, "MEDIA_DIR", tmp_path)
    monkeypatch.setattr(settings, "image_storage_endpoint", "")   # never upload to the real bucket from tests
    h = _login(db)
    buf = BytesIO()
    Image.new("RGB", (900, 600), "red").save(buf, "PNG")
    r = client.post("/api/v1/store/me/photo", headers=h, files={"file": ("me.png", buf.getvalue(), "image/png")})
    url = r.json()["data"]["profile_photo_url"]
    assert url.startswith("/media/avatars/")
    with Image.open(tmp_path / url.removeprefix("/media/")) as saved:
        assert saved.size == (256, 256)
    assert client.delete("/api/v1/store/me/photo", headers=h).json()["data"]["profile_photo_url"] is None


def test_non_image_photo_rejected(client, db):
    r = client.post("/api/v1/store/me/photo", headers=_login(db), files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 422


# ---- wishlist and bag on the account ----------------------------------------------------

def test_wishlist_and_bag_are_saved_and_merged_at_sign_in(client, db):
    from tests.wv_fixtures import make_variant
    a = make_variant(db, name="Silk Saree", qty=3)
    b = make_variant(db, name="Cotton Saree", qty=3)
    h = _login(db)
    client.put("/api/v1/store/me/shopping", headers=h, json={
        "wishlist": [str(a.product_id)], "cart": [{"variant_id": str(a.id), "qty": 1}]})
    # Guest picks in the browser, then signs in: both lists are joined, no duplicates.
    merged = client.post("/api/v1/store/me/shopping/merge", headers=h, json={
        "wishlist": [str(a.product_id), str(b.product_id)], "cart": [{"variant_id": str(b.id), "qty": 2}]}).json()["data"]
    assert [w["name"] for w in merged["wishlist"]] == ["Silk Saree", "Cotton Saree"]
    assert {c["variant"]["id"]: c["qty"] for c in merged["cart"]} == {str(a.id): 1, str(b.id): 2}
    # Another customer sees nothing of this.
    other = _login(db, phone="9822222222", email="b@example.com")
    assert client.get("/api/v1/store/me/shopping", headers=other).json()["data"] == {"wishlist": [], "cart": []}


def test_shopping_needs_login(client, db):
    assert client.get("/api/v1/store/me/shopping").status_code == 401
