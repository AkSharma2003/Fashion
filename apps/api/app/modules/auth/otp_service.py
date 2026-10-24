
import hashlib
import hmac
import secrets

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import redis_client


OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5


def _otp_key(phone_number: str) -> str:
    return f"fashionos:staff-otp:code:{phone_number.strip()}"


def _attempts_key(phone_number: str) -> str:
    return f"fashionos:staff-otp:attempts:{phone_number.strip()}"


def generate_staff_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_staff_otp(phone_number: str, otp: str) -> str:
    message = f"{phone_number.strip()}:{otp}".encode("utf-8")

    return hmac.new(
        settings.jwt_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def store_staff_otp(phone_number: str, otp: str) -> None:
    try:
        redis_client.set(
            _otp_key(phone_number),
            _hash_staff_otp(phone_number, otp),
            ex=OTP_TTL_SECONDS,
        )
        redis_client.set(
            _attempts_key(phone_number),
            0,
            ex=OTP_TTL_SECONDS,
        )
    except RedisError as exc:
        raise RuntimeError("OTP storage is temporarily unavailable") from exc


def verify_staff_otp(phone_number: str, otp: str) -> bool:
    if len(otp) != 6 or not otp.isdigit():
        return False

    try:
        stored_hash = redis_client.get(_otp_key(phone_number))

        if not stored_hash:
            return False

        attempts_key = _attempts_key(phone_number)
        attempts = int(redis_client.get(attempts_key) or 0)

        if attempts >= OTP_MAX_ATTEMPTS:
            return False

        expected_hash = _hash_staff_otp(phone_number, otp)

        if not hmac.compare_digest(stored_hash, expected_hash):
            redis_client.incr(attempts_key)
            redis_client.expire(attempts_key, OTP_TTL_SECONDS)
            return False

        return True
    

    except (RedisError, ValueError) as exc:
        raise RuntimeError("OTP verification is temporarily unavailable") from exc
    


def clear_staff_otp(phone_number: str) -> None:
    try:
        redis_client.delete(
            _otp_key(phone_number),
            _attempts_key(phone_number),
        )
    except RedisError as exc:
        raise RuntimeError("OTP cleanup is temporarily unavailable") from exc
