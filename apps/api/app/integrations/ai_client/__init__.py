"""Calls the separate AI service with a short timeout. Always has a fallback (SRS 6.2).

Never send full phone numbers, addresses, salary, balances or payment details.
"""
import logging

import httpx

from app.core.config import settings

log = logging.getLogger("wearverse.ai")


def compose_message(*, purpose: str, language: str, tone: str, first_name: str,
                    placeholders: list[str]) -> str | None:
    """Returns AI wording with placeholders, or None (caller uses the standard template)."""
    try:
        response = httpx.post(
            f"{settings.ai_service_url.rstrip('/')}/ai/message/compose",
            json={"purpose": purpose, "language": language, "tone": tone,
                  "first_name": first_name, "placeholders": placeholders},
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.info("AI compose unavailable, using template: %s", exc)
        return None
    if data.get("source") != "ai":
        return None
    text = data.get("text")
    return text if isinstance(text, str) and text.strip() else None
