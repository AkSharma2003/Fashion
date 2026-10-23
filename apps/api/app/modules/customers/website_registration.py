import hashlib
import hmac
import secrets

from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import redis_client


OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _otp_key(email: str) -> str:
    return f"fashionos:customer-registration:otp:{_normalize_email(email)}"


def _attempts_key(email: str) -> str:
    return f"fashionos:customer-registration:attempts:{_normalize_email(email)}"


def generate_otp() -> str:
    """Generate a cryptographically secure six-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, otp: str) -> str:
    """Create a keyed HMAC instead of a brute-forceable plain hash."""
    normalized_email = _normalize_email(email)
    message = f"{normalized_email}:{otp}".encode("utf-8")

    return hmac.new(
        settings.jwt_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def store_otp(email: str, otp: str) -> None:
    """Store an OTP hash for five minutes and reset attempts."""
    try:
        redis_client.set(
            _otp_key(email),
            hash_otp(email, otp),
            ex=OTP_TTL_SECONDS,
        )
        redis_client.set(
            _attempts_key(email),
            0,
            ex=OTP_TTL_SECONDS,
        )
    except RedisError as exc:
        raise RuntimeError("OTP storage is temporarily unavailable") from exc


def verify_stored_otp(email: str, otp: str) -> bool:
    """Verify an OTP and limit incorrect attempts."""
    if len(otp) != 6 or not otp.isdigit():
        return False

    try:
        stored_hash = redis_client.get(_otp_key(email))

        if not stored_hash:
            return False

        attempts_key = _attempts_key(email)
        attempts = int(redis_client.get(attempts_key) or 0)

        if attempts >= OTP_MAX_ATTEMPTS:
            return False

        if not hmac.compare_digest(
            stored_hash,
            hash_otp(email, otp),
        ):
            redis_client.incr(attempts_key)
            redis_client.expire(attempts_key, OTP_TTL_SECONDS)
            return False

        return True

    except (RedisError, ValueError) as exc:
        raise RuntimeError("OTP verification is temporarily unavailable") from exc


def clear_otp(email: str) -> None:
    """Delete the OTP and attempt counter after successful verification."""
    try:
        redis_client.delete(
            _otp_key(email),
            _attempts_key(email),
        )
    except RedisError as exc:
        raise RuntimeError("OTP cleanup is temporarily unavailable") from exc
    
    
import json

PENDING_REGISTRATION_TTL_SECONDS = 300


def _pending_registration_key(email: str) -> str:
    return (
        "fashionos:customer-registration:pending:"
        f"{_normalize_email(email)}"
    )


def store_pending_registration(
    email: str,
    registration_data: dict,
) -> None:
    """Store pending registration data temporarily in Redis."""
    try:
        redis_client.set(
            _pending_registration_key(email),
            json.dumps(registration_data),
            ex=PENDING_REGISTRATION_TTL_SECONDS,
        )
    except RedisError as exc:
        raise RuntimeError(
            "Pending registration storage is temporarily unavailable"
        ) from exc


def get_pending_registration(email: str) -> dict | None:
    """Retrieve pending registration data from Redis."""
    try:
        raw_data = redis_client.get(
            _pending_registration_key(email)
        )
        if not raw_data:
            return None

        data = json.loads(raw_data)
        return data if isinstance(data, dict) else None

    except (RedisError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Pending registration lookup is temporarily unavailable"
        ) from exc


def clear_pending_registration(email: str) -> None:
    """Delete pending registration data after verification."""
    try:
        redis_client.delete(_pending_registration_key(email))
    except RedisError as exc:
        raise RuntimeError(
            "Pending registration cleanup is temporarily unavailable"
        ) from exc
