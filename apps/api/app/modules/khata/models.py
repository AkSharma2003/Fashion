import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class KhataAccount(Base):
    __tablename__ ="khata_accounts"
    
    id:Mapped[uuid.UUID]=mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    
    
    customer_id:Mapped[uuid.UUID]=mapped_column(
        ForeignKey("customers.id"),
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
    
    