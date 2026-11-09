"""Business rules and integrations (Settings -> Rules), served at /api/v1/settings. Owner/Admin only."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.app_settings import DEFAULTS, all_settings, set_setting
from app.core.audit import write_audit
from app.core.config import settings as env
from app.core.db import get_db
from app.core.errors import BusinessError, ok
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import StaffUser

router = APIRouter()
READ_ONLY = {"tally_agent_last_seen", "tally_last_alter_id"}


@router.get("")
def get_settings(db: Session = Depends(get_db), user: StaffUser = Depends(require_role())):
    values = all_settings(db)
    return ok({"rules": values, "integrations": {
        "razorpay": bool(env.razorpay_key_id), "whatsapp": bool(env.whatsapp_provider_url),
        "sms": bool(env.twofactor_api_key), "tally_agent": bool(env.tally_agent_api_key),
        "shiprocket": bool(env.shiprocket_email), "ai_service_url": env.ai_service_url,
        "environment": env.environment}})


@router.patch("")
def update_settings(payload: dict[str, Any], db: Session = Depends(get_db), user: StaffUser = Depends(require_role())):
    changed = {}
    for key, value in payload.items():
        if key in READ_ONLY or (key not in DEFAULTS and key != "pos_mode"):
            raise BusinessError("VALIDATION_ERROR", f"'{key}' is not a setting you can change here.", 400)
        if key == "tally_mode":
            raise BusinessError("VALIDATION_ERROR", "Change Tally mode from the Tally screen.", 400)
        old = set_setting(db, key, value, str(user.id))
        changed[key] = {"old": old, "new": value}
    write_audit(db, actor_id=str(user.id), action="update", entity="settings", entity_id="rules", new_value=changed)
    db.commit()
    return ok(all_settings(db))
