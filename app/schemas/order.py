from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
class AddToCart(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    quantity: int
    price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    total: Decimal
    items: list[OrderItemRead]