"""Owner / Admin / Manager see registered website users and give them a staff role (with limits).
Every role change needs the changer's own password and a reason, and is kept in the role history."""
from app.core.security import hash_password
from app.modules.customers.models import Customer

from tests.wv_fixtures import auth, client, db, engine, make_user  # noqa: F401

PW = "mypass123"


def _customer(db, phone="9811111111", name="Asha Verma", password="secret12"):
    c = Customer(full_name=name, phone_number=phone, email=f"{phone}@example.com",
                 password_hash=hash_password(password) if password else None, is_active=True, is_verified=True)
    db.add(c)
    db.commit()
    return c


def boss(db, role):
    return make_user(db, role, password=PW)


def give(client, actor, c, role, **extra):
    return client.post(f"/api/v1/auth/registered-users/{c.id}/role", headers=auth(actor),
                       json={"role": role, "confirm_password": PW, "reason": "Joined the counter team", **extra})


def test_manager_gives_cashier_role_then_they_sign_in_as_staff(client, db):
    c = _customer(db)
    manager = boss(db, "Manager")
    listing = client.get("/api/v1/auth/registered-users", headers=auth(manager)).json()["data"]
    assert listing["can_give"] == ["Cashier", "OnlineStaff", "Supervisor", "Employee"]
    assert give(client, manager, c, "Cashier").json()["data"]["staff"]["role"] == "Cashier"
    signed = client.post("/api/v1/auth/sign-in", json={"login": "9811111111", "password": "secret12"}).json()["data"]
    assert signed["kind"] == "staff" and signed["role"] == "Cashier"
    client.post(f"/api/v1/auth/registered-users/{c.id}/role/remove", headers=auth(manager),
                json={"confirm_password": PW, "reason": "Left the job"})
    again = client.post("/api/v1/auth/sign-in", json={"login": "9811111111", "password": "secret12"}).json()["data"]
    assert again["kind"] == "customer"


def test_wrong_password_or_missing_reason_changes_nothing(client, db):
    c = _customer(db)
    manager = boss(db, "Manager")
    r = client.post(f"/api/v1/auth/registered-users/{c.id}/role", headers=auth(manager),
                    json={"role": "Cashier", "confirm_password": "wrong", "reason": "Joined the counter team"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "CONFIRM_FAILED"
    r = client.post(f"/api/v1/auth/registered-users/{c.id}/role", headers=auth(manager),
                    json={"role": "Cashier", "confirm_password": PW, "reason": "ok"})
    assert r.status_code == 422
    assert client.get("/api/v1/auth/registered-users", headers=auth(manager)).json()["data"]["users"][0]["staff"] is None


def test_role_history_keeps_who_what_why(client, db):
    c = _customer(db)
    owner = boss(db, "Owner")
    give(client, owner, c, "Cashier")
    give(client, owner, c, "Accountant", reason="Moved to accounts after training")
    rows = client.get("/api/v1/auth/role-history", headers=auth(owner)).json()["data"]
    # (SQLite keeps whole seconds, so two changes in one second may come in either order here.)
    assert {(r["from_role"], r["to_role"], r["reason"]) for r in rows} == {
        ("Cashier", "Accountant", "Moved to accounts after training"), (None, "Cashier", "Joined the counter team")}
    assert {r["by"] for r in rows} == {"Owner user"} and {r["user"] for r in rows} == {"Asha Verma"}


def test_manager_cannot_give_or_change_higher_roles(client, db):
    c = _customer(db)
    manager = boss(db, "Manager")
    assert give(client, manager, c, "Manager").status_code == 403
    assert give(client, boss(db, "Owner"), c, "Accountant").status_code == 200
    assert give(client, manager, c, "Cashier").status_code == 403
    r = client.post(f"/api/v1/auth/registered-users/{c.id}/role/remove", headers=auth(manager),
                    json={"confirm_password": PW, "reason": "Trying to remove"})
    assert r.status_code == 403


def test_only_owner_makes_an_admin_and_cashiers_cannot_see_users(client, db):
    c = _customer(db)
    admin = boss(db, "Admin")
    assert give(client, admin, c, "Owner").status_code == 403
    assert give(client, admin, c, "Admin").status_code == 200
    assert client.get("/api/v1/auth/registered-users", headers=auth(make_user(db, "Cashier"))).status_code == 403


def test_user_without_password_needs_one_for_staff_login(client, db):
    c = _customer(db, phone="9822222222", password=None)          # e.g. a khata customer made at the counter
    owner = boss(db, "Owner")
    assert give(client, owner, c, "Employee").status_code == 422
    assert give(client, owner, c, "Employee", password="newpass1").status_code == 200


def test_customers_are_normal_until_made_khata_and_closing_needs_zero_balance(client, db):
    from app.modules.khata import ledger
    from app.modules.khata.models import KhataAccount
    c = _customer(db)
    manager = boss(db, "Manager")
    row = client.get("/api/v1/auth/registered-users", headers=auth(manager)).json()["data"]["users"][0]
    assert row["type"] == "normal" and row["khata"] is None
    assert client.post(f"/api/v1/khata/customers/{c.id}/make-khata", headers=auth(manager), json={"credit_limit_paise": 500000}).status_code == 200
    khata = client.get("/api/v1/auth/registered-users?type=khata", headers=auth(manager)).json()["data"]["users"]
    assert [u["full_name"] for u in khata] == ["Asha Verma"] and khata[0]["khata"]["credit_limit_paise"] == 500000
    account = db.query(KhataAccount).filter_by(customer_id=c.id).one()
    ledger.post_entry(db, account.id, "SALE", 120000, ref_type="bill", ref_label="Bill 1", created_by="t")
    db.commit()
    blocked = client.post(f"/api/v1/khata/customers/{c.id}/make-normal", headers=auth(manager))
    assert blocked.status_code == 422 and "owes" in blocked.json()["error"]["message"]
    ledger.post_entry(db, account.id, "PAYMENT", -120000, ref_type="payment", ref_label="Paid", created_by="t")
    db.commit()
    assert client.post(f"/api/v1/khata/customers/{c.id}/make-normal", headers=auth(manager)).status_code == 200
    client.post(f"/api/v1/khata/customers/{c.id}/make-khata", headers=auth(manager), json={})
    assert db.query(KhataAccount).filter_by(customer_id=c.id).count() == 1
