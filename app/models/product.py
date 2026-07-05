from decimal import Decimal
from sqlalchemy import Numeric,String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200),index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(default=None)   