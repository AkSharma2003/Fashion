"""Gap-free running numbers (FP job tags, order numbers, return numbers, purchase numbers)."""
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    name: Mapped[str] = mapped_column(String(48), primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, default=1)


def next_number(db: Session, name: str) -> int:
    row = db.scalar(select(NumberSequence).where(NumberSequence.name == name).with_for_update())
    if row is None:
        row = NumberSequence(name=name, next_value=1)
        db.add(row)
        db.flush()
    value = row.next_value
    row.next_value = value + 1
    db.flush()
    return value


def formatted(db: Session, name: str, prefix: str, width: int = 6) -> str:
    return f"{prefix}{next_number(db, name):0{width}d}"
