"""Simple fixed-window rate limit in Redis (login, OTP, Pay Now links, chatbot).

If Redis is down the request is allowed (availability over strictness) and logged.
"""
import logging

from fastapi import Request
from redis.exceptions import RedisError

from app.core.errors import BusinessError

log = logging.getLogger("wearverse.ratelimit")


def client_ip(request: Request) -> str:
    """The caller's IP. Behind Caddy, the proxy appends the real address as the LAST X-Forwarded-For entry;
    earlier entries are whatever the client sent and must not be trusted (they could dodge the limit)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "?"


def rate_limit(name: str, limit: int, window_seconds: int):
    def dependency(request: Request) -> None:
        from app.core.redis import redis_client
        key = f"wearverse:rl:{name}:{client_ip(request)}"
        try:
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, window_seconds)
        except (RedisError, OSError) as exc:
            log.warning("rate limit skipped (redis): %s", exc)
            return
        if count > limit:
            raise BusinessError("RATE_LIMITED", "Too many requests. Please wait a minute.", 429)

    return dependency
