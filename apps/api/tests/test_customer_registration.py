
import pytest
from unittest.mock import patch

from app.modules.customers import website_registration as registration


@pytest.fixture()
def fake_redis():
    store = {}
    ttls = {}

    class FakeRedis:
        def set(self, key, value, ex=None):
            store[key] = str(value)
            if ex is not None:
                ttls[key] = ex
            return True

        def get(self, key):
            return store.get(key)

        def incr(self, key):
            store[key] = str(int(store.get(key, "0")) + 1)
            return int(store[key])

        def expire(self, key, seconds):
            ttls[key] = seconds
            return True

        def delete(self, *keys):
            deleted = 0
            for key in keys:
                if key in store:
                    del store[key]
                    deleted += 1
                ttls.pop(key, None)
            return deleted

    fake = FakeRedis()

    with patch.object(registration, "redis_client", fake):
        yield fake, store, ttls


def test_generate_otp_is_six_digits():
    otp = registration.generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()


def test_store_and_verify_correct_otp(fake_redis):
    _, store, _ = fake_redis
    email = "Customer@Example.com"
    otp = "123456"

    registration.store_otp(email, otp)

    assert registration.verify_stored_otp(email.lower(), otp) is True
    assert registration._otp_key(email) in store


def test_wrong_otp_increments_attempt_count(fake_redis):
    _, store, _ = fake_redis
    email = "customer@example.com"

    registration.store_otp(email, "123456")

    assert registration.verify_stored_otp(email, "000000") is False
    assert store[registration._attempts_key(email)] == "1"


def test_otp_is_rejected_after_maximum_attempts(fake_redis):
    _, store, _ = fake_redis
    email = "customer@example.com"

    registration.store_otp(email, "123456")
    attempts_key = registration._attempts_key(email)
    store[attempts_key] = str(registration.OTP_MAX_ATTEMPTS)

    assert registration.verify_stored_otp(email, "123456") is False


@pytest.mark.parametrize("otp", ["12345", "1234567", "abcdef", "12a456"])
def test_invalid_otp_format_is_rejected(otp):
    assert registration.verify_stored_otp("customer@example.com", otp) is False


def test_clear_otp_removes_otp_and_attempts(fake_redis):
    _, store, _ = fake_redis
    email = "customer@example.com"

    registration.store_otp(email, "123456")
    registration.clear_otp(email)

    assert registration._otp_key(email) not in store
    assert registration._attempts_key(email) not in store


def test_pending_registration_is_stored_and_retrieved(fake_redis):
    _, _, _ = fake_redis
    email = "Customer@Example.com"
    data = {"full_name": "Test Customer", "email": "customer@example.com"}

    registration.store_pending_registration(email, data)

    assert registration.get_pending_registration(email.lower()) == data


def test_clear_pending_registration_removes_data(fake_redis):
    _, store, _ = fake_redis
    email = "customer@example.com"

    registration.store_pending_registration(email, {"full_name": "Test"})
    registration.clear_pending_registration(email)

    assert registration.get_pending_registration(email) is None
    assert registration._pending_registration_key(email) not in store


def test_otp_is_stored_as_hash_with_five_minute_ttl(fake_redis):
    _, store, ttls = fake_redis
    email = "customer@example.com"
    otp = "123456"

    registration.store_otp(email, otp)

    otp_key = registration._otp_key(email)
    attempts_key = registration._attempts_key(email)

    # OTP should not be stored as plain text.
    assert store[otp_key] != otp
    assert len(store[otp_key]) == 64

    # Both keys should have a five-minute TTL configured.
    assert ttls[otp_key] == registration.OTP_TTL_SECONDS
    assert ttls[attempts_key] == registration.OTP_TTL_SECONDS


def test_correct_otp_is_rejected_after_five_wrong_attempts(fake_redis):
    _, store, _ = fake_redis
    email = "customer@example.com"
    correct_otp = "123456"

    registration.store_otp(email, correct_otp)

    # Five incorrect attempts should exhaust the limit.
    for _ in range(registration.OTP_MAX_ATTEMPTS):
        assert registration.verify_stored_otp(email, "000000") is False

    attempts_key = registration._attempts_key(email)
    assert store[attempts_key] == str(registration.OTP_MAX_ATTEMPTS)

    # Even the correct OTP should now be rejected.
    assert registration.verify_stored_otp(email, correct_otp) is False


def test_pending_registration_has_five_minute_ttl(fake_redis):
    _, _, ttls = fake_redis
    email = "customer@example.com"

    registration.store_pending_registration(
        email,
        {"full_name": "Test Customer"},
    )

    pending_key = registration._pending_registration_key(email)

    assert ttls[pending_key] == (
        registration.PENDING_REGISTRATION_TTL_SECONDS
    )