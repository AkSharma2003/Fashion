"""Simple fixed-window rate limit in Redis (login, OTP, Pay Now links, chatbot).

If Redis is down the request is allowed (availability over strictness) and logged.
"""
import logging

from fastapi import Request
from redis.exceptions import RedisError

from app.core.errors import BusinessError

log = logging.getLogger("wearverse.ratelimit")


def rate_limit(name: str, limit: int, window_seconds: int):
    def dependency(request: Request) -> None:
        from app.core.redis import redis_client
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "?")
        key = f"wearverse:rl:{name}:{client_ip.split(',')[0].strip()}"
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
