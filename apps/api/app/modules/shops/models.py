import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Shop(Base):
    """One shop of the business (e.g. Sethi Saree Sansar, Sethi Suit, Sethi Kids).
    Each shop is its own GST business: own GSTIN, bill series, Tally company, stock and khata."""
    __tablename__ = "shops"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(8), unique=True)            # SSS / SS / SK, also the bill prefix
    name: Mapped[str] = mapped_column(String(100))
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    tally_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)       # the website / default shop
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
