
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    category: str = Field(min_length=1, max_length=100)
    selling_price_paise: int = Field(ge=0)
    mrp_paise: int | None = Field(default=None, ge=0)
    gst_rate_bp: int | None = Field(default=None, ge=0, le=2800)
    hsn_code: str | None = Field(default=None, max_length=16)
    fall_pico_eligible: bool = False


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    selling_price_paise: int | None = Field(default=None, ge=0)
    mrp_paise: int | None = Field(default=None, ge=0)
    gst_rate_bp: int | None = Field(default=None, ge=0, le=2800)
    hsn_code: str | None = Field(default=None, max_length=16)
    fall_pico_eligible: bool | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    sku: str
    barcode: str | None
    category: str
    selling_price_paise: int
    mrp_paise: int | None = None
    gst_rate_bp: int | None = None
    hsn_code: str | None = None
    fall_pico_eligible: bool = False
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Variants as the product screens use them (size / colour / price / stock).
class CatalogVariantCreate(BaseModel):
    size: str = Field(default="", max_length=50)
    color: str = Field(default="", max_length=50)
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    selling_price_paise: int | None = Field(default=None, ge=0)
    mrp_paise: int | None = Field(default=None, ge=0)
    cost_paise: int | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)


class CatalogVariantUpdate(BaseModel):
    size: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    selling_price_paise: int | None = Field(default=None, ge=0)
    mrp_paise: int | None = Field(default=None, ge=0)
    cost_paise: int | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
