import uuid

from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class Customer(Base):
    __tablename__ ="customers"
    
    id:Mapped[uuid.UUID] =mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    
    full_name:Mapped[str]=mapped_column(
        String(100),
        nullable=False,
    )
    
    phone_number:Mapped[str]=mapped_column(
        String(15),
        unique=True,
        nullable=False,
    )
    
    is_active:Mapped[bool]=mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    
    updated_at:Mapped[datetime]=mapped_column(
            DateTime(timezone=True),
            default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )