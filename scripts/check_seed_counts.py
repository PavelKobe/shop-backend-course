import asyncio

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.category import Category
from app.models.product import Product


async def main() -> None:
    async with SessionLocal() as session:
        category_count = await session.scalar(
            select(func.count())
            .select_from(Category)
            .where(Category.slug.like("lesson-category-%"))
        )
        product_count = await session.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.slug.like("lesson-product-%"))
        )
        linked_product_count = await session.scalar(
            select(func.count())
            .select_from(Product)
            .where(
                Product.slug.like("lesson-product-%"),
                Product.category_id.is_not(None),
            )
        )

    print(f"lesson_categories={category_count}")
    print(f"lesson_products={product_count}")
    print(f"lesson_products_with_category={linked_product_count}")


if __name__ == "__main__":
    asyncio.run(main())
