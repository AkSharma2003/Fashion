"""Business rules the owner can change (Settings -> Rules). Stored as key/value JSON.

Every key has a default here, so a fresh database works without seeding.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


DEFAULTS: dict[str, Any] = {
    # Shop
    "shop_name": "WearVerse",
    "shop_gstin": "",
    "shop_state_code": "",
    # Tally (SRS 3.18): "A" = counter bills in TallyPrime, "B" = counter bills in WearVerse POS.
    "tally_mode": "A",
    "tally_cutover_date": None,
    "tally_working_hours": {"start": "00:00", "end": "23:59"},
    "tally_alert_after_minutes": 30,
    "tally_max_attempts_before_issue": 5,
    # Fall-pico: one job per eligible saree priced ABOVE this (after discount).
    "fall_pico_limit_paise": 100000,
    "fall_pico_default_days": 3,
    # GST slabs for apparel when the product has no fixed rate [Assumption: confirm with CA].
    # Prices are GST-inclusive. A unit price up to max_paise uses rate_bp (500 = 5%).
    "gst_slabs": [{"max_paise": 250000, "rate_bp": 500}, {"max_paise": None, "rate_bp": 1800}],
    # Discounts: highest discount % (of line value) each role may give without a manager PIN.
    "discount_limit_percent": {"Cashier": 5, "Manager": 20, "Owner": 100, "Admin": 100},
    # Khata
    "khata_default_limit_paise": 1000000,
    "khata_default_credit_days": 30,
    "khata_offline_limit_percent": 80,
    "reminder_days_after_bill": [7, 15, 30],
    "reminder_weekly_after_due": True,
    "quiet_hours": {"start": "21:00", "end": "09:00"},
    "paylink_valid_days": 7,
    # Website
    "reservation_minutes": 30,
    "return_days": 7,
    "shipping_fee_paise": 0,
    "free_shipping_above_paise": 0,
    "shiprocket_pickup_location": "Primary",
    "shiprocket_package": {"length": 30, "breadth": 25, "height": 4, "weight": 0.6},
    # Employees
    "weekly_off_paid": True,
    "advance_limit_paise": 1000000,
    # AI (SRS 6.2): each feature has an on/off switch; all of them share a monthly cost cap.
    "ai_features": {"message": True, "recommend": True, "chat": True, "search": True, "size": True,
                    "describe": True, "poster": True, "visual": True, "forecast": True, "buying": True},
    "ai_monthly_budget_paise": 500000,
    # Estimated cost per million tokens in paise (input, output) to track spend [Assumption: check the bill].
    "ai_cost_paise_per_mtok": {"input": 34000, "output": 170000},
    "chat_retention_days": 90,
    # Size help (body measurements in cm). The smallest size whose limit fits is suggested.
    "size_charts": {
        "Suits": [{"size": "S", "bust": 86, "waist": 71}, {"size": "M", "bust": 91, "waist": 76},
                  {"size": "L", "bust": 97, "waist": 81}, {"size": "XL", "bust": 102, "waist": 86},
                  {"size": "XXL", "bust": 107, "waist": 91}, {"size": "3XL", "bust": 112, "waist": 97}],
        "Kids": [{"size": "2-3Y", "height": 98}, {"size": "3-4Y", "height": 104}, {"size": "4-5Y", "height": 110},
                 {"size": "5-6Y", "height": 116}, {"size": "6-7Y", "height": 122}, {"size": "7-8Y", "height": 128},
                 {"size": "8-9Y", "height": 134}, {"size": "9-10Y", "height": 140}],
    },
    # "Complete the look": which categories go with which.
    "complete_the_look": {"Sarees": ["Blouse", "Petticoat", "Jewellery"], "Suits": ["Dupatta", "Leggings", "Jewellery"],
                          "Kids": ["Kids"], "Lehenga": ["Dupatta", "Jewellery"]},
    # Help answers for the chatbot and the FAQ fallback (owner can edit in Settings).
    "faq": [
        {"q": "delivery shipping kitne din days", "a": "Orders are packed in 1-2 days and delivered in 3-7 days across India. You get the tracking number on WhatsApp."},
        {"q": "return exchange wapas", "a": "You can return unused items within 7 days of delivery. Write to us with your order number and we arrange the pickup; the refund goes back to your payment method."},
        {"q": "fall pico falls", "a": "Fall-pico is free on eligible sarees. Online orders with fall-pico ship 2-3 days later; you can skip it at checkout."},
        {"q": "cod cash on delivery", "a": "Cash on delivery is available. Online payment by UPI, card or net banking is also accepted."},
        {"q": "shop address timing open", "a": "Our shop is open 11 am to 9 pm, all days. Call or WhatsApp us for directions."},
    ],
}


def get_setting(db: Session, key: str) -> Any:
    row = db.get(AppSetting, key)
    if row is not None:
        return row.value
    return DEFAULTS.get(key)


def all_settings(db: Session) -> dict[str, Any]:
    values = dict(DEFAULTS)
    for row in db.query(AppSetting).all():
        values[row.key] = row.value
    return values


def set_setting(db: Session, key: str, value: Any, actor_id: str | None = None) -> Any:
    row = db.get(AppSetting, key)
    old = row.value if row else DEFAULTS.get(key)
    if row is None:
        db.add(AppSetting(key=key, value=value, updated_by=actor_id))
    else:
        row.value = value
        row.updated_by = actor_id
    db.flush()
    return old
