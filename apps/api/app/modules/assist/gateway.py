"""Every AI call goes through here (SRS 6.2):
on/off switch per feature, shared monthly cost cap (alert at 80 %), usage logging, short timeout,
and None on any failure so the caller shows its non-AI fallback.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.alerts import raise_alert
from app.core.app_settings import get_setting
from app.core.config import settings
from app.modules.assist.models import AiUsage

log = logging.getLogger("wearverse.ai")


def feature_on(db: Session, feature: str) -> bool:
    flags = get_setting(db, "ai_features") or {}
    return bool(flags.get(feature, True))


def month_spend_paise(db: Session) -> int:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    return int(db.scalar(select(func.coalesce(func.sum(AiUsage.cost_paise), 0)).where(AiUsage.created_at >= start)) or 0)


def _cost(db: Session, usage: dict) -> int:
    rates = get_setting(db, "ai_cost_paise_per_mtok") or {"input": 0, "output": 0}
    return (int(usage.get("input_tokens", 0)) * int(rates["input"]) + int(usage.get("output_tokens", 0)) * int(rates["output"])) // 1_000_000


def record(db: Session, feature: str, source: str, usage: dict | None = None) -> None:
    usage = usage or {}
    db.add(AiUsage(feature=feature, source=source, input_tokens=int(usage.get("input_tokens", 0)),
                   output_tokens=int(usage.get("output_tokens", 0)), cost_paise=_cost(db, usage)))
    db.flush()


def ask(db: Session, feature: str, path: str, payload: dict, timeout: float | None = None) -> dict | None:
    """POST to the AI service. Returns its JSON when source == 'ai', else None."""
    if not feature_on(db, feature):
        return None
    budget = int(get_setting(db, "ai_monthly_budget_paise") or 0)
    spent = month_spend_paise(db)
    if budget and spent >= budget:
        raise_alert(db, "AI_BUDGET", "AI monthly budget is used up; AI features fall back until next month.",
                    severity="warning", dedupe_key=f"ai_budget:{datetime.now(timezone.utc):%Y-%m}")
        return None
    try:
        response = httpx.post(f"{settings.ai_service_url.rstrip('/')}{path}", json=payload,
                              timeout=timeout or settings.ai_timeout_seconds)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.info("AI %s unavailable, fallback used: %s", feature, exc)
        record(db, feature, "fallback")
        return None
    record(db, feature, data.get("source", "fallback"), data.get("usage"))
    if budget and spent < budget * 0.8 <= month_spend_paise(db):
        raise_alert(db, "AI_BUDGET", "AI spend passed 80% of the monthly budget.", severity="warning",
                    dedupe_key=f"ai_budget80:{datetime.now(timezone.utc):%Y-%m}")
    return data if data.get("source") == "ai" else None
