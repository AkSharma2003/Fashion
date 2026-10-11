
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    category: str = Field(min_length=1, max_length=100)
    selling_price_paise: int = Field(ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    selling_price_paise: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    sku: str
    barcode: str | None
    category: str
    selling_price_paise: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)