"""Shared test setup: an in-memory stand-in for Redis so tests never depend on (or fill up) a real Redis."""
import pytest


class FakeRedis:
    def __init__(self):
        self.data: dict[str, int] = {}

    def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    def expire(self, key, seconds):
        return True

    def __getattr__(self, name):          # anything else (get/set/delete for OTPs) behaves like an empty store
        store = self.__dict__.setdefault("kv", {})
        if name == "set":
            return lambda k, v, ex=None, **kw: store.__setitem__(k, v) or True
        if name == "setex":
            return lambda k, ttl, v: store.__setitem__(k, v) or True
        if name == "get":
            return lambda k: store.get(k)
        if name == "delete":
            return lambda *ks: sum(1 for k in ks if store.pop(k, None) is not None)
        raise AttributeError(name)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    from app.core import redis as redis_module
    fake = FakeRedis()
    monkeypatch.setattr(redis_module, "redis_client", fake)
    for mod in ("app.modules.customers.website_registration", "app.modules.auth.otp_service"):
        try:
            m = __import__(mod, fromlist=["redis_client"])
            if hasattr(m, "redis_client"):
                monkeypatch.setattr(m, "redis_client", fake)
        except ImportError:
            pass
    return fake
