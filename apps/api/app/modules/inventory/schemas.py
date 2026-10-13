
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Create a product variant
class VariantCreate(BaseModel):
    product_id: UUID
    sku: str = Field(min_length=1, max_length=64)
    size: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=128)


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    sku: str
    size: str | None = None
    color: str | None = None


# Adjust stock quantity
class StockAdjustment(BaseModel):
    variant_id: UUID
    quantity_delta: int
    reason: str = Field(min_length=1, max_length=500)


class StockResponse(BaseModel):
    variant_id: UUID
    on_hand: int
    reserved: int
    available: int


# Record physical stock count
class StockCountCreate(BaseModel):
    variant_id: UUID
    counted_quantity: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


class StockCountResponse(BaseModel):
    id: UUID
    variant_id: UUID
    expected_quantity: int
    counted_quantity: int
    difference: int
    reason: str | None = None
