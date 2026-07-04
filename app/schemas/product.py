from decimal import Decimal
from pydantic import BaseModel, ConfigDict,Field

class ProductCreate(BaseModel):
    name: str = Field(min_length=1,max_length=200)
    price: Decimal = Field(gt=0,max_digits=10,decimal_places=2)
    description: str | None = None

 class ProductUpdate(BaseModel):
    name: str | None = Field(default=None,max_length=1,min_length=200)
    price: Decimal | None = Field(default=None,gt=0)
    description: str | None = None

class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: Decimal
    description: str | None = None
