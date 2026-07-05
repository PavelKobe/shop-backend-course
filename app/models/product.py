from decimal import Decimal
from sqlalchemy import Numeric,String,ForeignKey
from sqlalchemy.orm import Mapped, mapped_column,relationship
from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(default=None)
    stock: Mapped[int] = mapped_column(default=0)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    category: Mapped["Category | None"] = relationship(back_populates="products")
from app.models.category import Category   