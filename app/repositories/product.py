from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, skip: int, limit: int) -> Sequence[Product]:
        stmt = select(Product).offset(skip).limit(limit).order_by(Product.id)
        return (await self.session.scalars(stmt)).all()

    async def get(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get_by_slug(self, slug: str) -> Product | None:
        stmt = select(Product).where(Product.slug == slug)
        return await self.session.scalar(stmt)

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.session.delete(product)
        await self.session.commit()
