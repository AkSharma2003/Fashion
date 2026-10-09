import uuid
from datetime import datetime


from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class Role(Base):
    __tablename__ = "roles"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )
    
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    staff_users=relationship(
        "StaffUser", 
        back_populates="role"
    )

# class User(Base):
#     __tablename__ = "users"
    
#     id: Mapped[uuid.UUID] = mapped_column(
#         Uuid, 
#         primary_key=True, 
#         default=uuid.uuid4
#     )
    
#     email: Mapped[str] = mapped_column(
#         String(50),
#         unique=True,
#         nullable=False
#     )
    
#     description: Mapped[str] = mapped_column(
#         String(255),
#         nullable=True
#     )
    
#     is_active: Mapped[bool] = mapped_column(
#         Boolean,
#         default=True,
#         nullable=False
#     )
    
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         default=func.now(),
#         nullable=False
#     )
    
#     updated_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         default=func.now(),
#         onupdate=func.now(),
#         nullable=False
#     )
    
#     staff_user=relationship(
#         "StaffUser", 
#         back_populates="user"
#     )
    
class StaffUser(Base):
    __tablename__ = "staff_users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    full_name: Mapped[str]=mapped_column(
        String(50),
        nullable=False
    )
    
    phone_number: Mapped[str]=mapped_column(
        String(15),
        unique=True,
        nullable=False
    )
    
    password_hash: Mapped[str]=mapped_column(
        String(255),
        nullable=True
    )
    
    pin_hash: Mapped[str | None]=mapped_column(
        String(255),
        nullable=True
    )
    
    role_id: Mapped[uuid.UUID]=mapped_column(
        ForeignKey("roles.id"),
        nullable=False
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
        
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
    )
        
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
    
    # user=relationship(
    #     "User", 
    #     back_populates="staff_user"
    # )

    role=relationship(
        "Role", 
        back_populates="staff_users"
    )
