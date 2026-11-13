"""Staff logins in Settings: the shop can never lock itself out of the Owner role."""
from tests.wv_fixtures import auth, client, db, engine, make_user  # noqa: F401


PW = "mypass123"
OK = {"confirm_password": PW, "reason": "Testing the safety rules"}


def test_owner_cannot_demote_themselves(client, db):
    owner = make_user(db, "Owner", password=PW)
    r = client.patch(f"/api/v1/auth/users/{owner.id}", json={"role": "Manager", **OK}, headers=auth(owner))
    assert r.status_code == 403
    r = client.patch(f"/api/v1/auth/users/{owner.id}", json={"is_active": False, **OK}, headers=auth(owner))
    assert r.status_code == 403


def test_last_owner_cannot_be_removed_but_second_owner_can(client, db):
    o1, o2 = make_user(db, "Owner", password=PW), make_user(db, "Owner")
    assert client.patch(f"/api/v1/auth/users/{o2.id}", json={"role": "Manager", **OK}, headers=auth(o1)).status_code == 200
    # Now o1 is the only Owner; even an Admin cannot touch it, and o1 cannot demote itself.
    admin = make_user(db, "Admin", password=PW)
    assert client.patch(f"/api/v1/auth/users/{o1.id}", json={"is_active": False, **OK}, headers=auth(admin)).status_code == 403


def test_only_owner_gives_owner_role(client, db):
    admin = make_user(db, "Admin", password=PW)
    r = client.post("/api/v1/auth/users", headers=auth(admin),
                    json={"full_name": "New Owner", "phone_number": "9000000099", "role": "Owner", "password": "secret12", "confirm_password": PW})
    assert r.status_code == 403
    r = client.post("/api/v1/auth/users", headers=auth(admin),
                    json={"full_name": "Cashier One", "phone_number": "9000000098", "role": "Cashier", "password": "secret12", "confirm_password": PW})
    assert r.status_code == 201


def test_manager_cannot_manage_logins(client, db):
    assert client.get("/api/v1/auth/users", headers=auth(make_user(db, "Manager"))).status_code == 403


def test_role_change_in_settings_needs_password_and_reason(client, db):
    owner = make_user(db, "Owner", password=PW)
    cashier = make_user(db, "Cashier")
    r = client.patch(f"/api/v1/auth/users/{cashier.id}", json={"role": "Manager"}, headers=auth(owner))
    assert r.status_code == 403 and r.json()["error"]["code"] == "CONFIRM_FAILED"
    assert client.patch(f"/api/v1/auth/users/{cashier.id}", json={"role": "Manager", **OK}, headers=auth(owner)).status_code == 200
    # Changing only the name needs no password.
    assert client.patch(f"/api/v1/auth/users/{cashier.id}", json={"full_name": "New Name"}, headers=auth(owner)).status_code == 200
