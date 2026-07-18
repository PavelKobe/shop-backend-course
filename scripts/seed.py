import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.category import Category
from app.models.product import Product

CATEGORY_COUNT = 100
PRODUCT_COUNT = 500


def category_data(index: int) -> dict[str, str]:
    return {
        "name": f"Учебная категория {index:03d}",
        "slug": f"lesson-category-{index:03d}",
    }


def product_data(index: int, category_id: int) -> dict:
    price = Decimal(100 + index * 7).quantize(Decimal("0.01"))
    return {
        "name": f"Учебный товар {index:03d}",
        "slug": f"lesson-product-{index:03d}",
        "price": price,
        "description": f"Тестовый товар {index:03d} для урока с Redis.",
        "stock": 10 + index % 90,
        "category_id": category_id,
    }


async def seed() -> None:
    async with SessionLocal() as session:
        categories_by_slug = {
            category.slug: category
            for category in (
                await session.scalars(
                    select(Category).where(Category.slug.like("lesson-category-%"))
                )
            ).all()
        }

        categories: list[Category] = []
        for index in range(1, CATEGORY_COUNT + 1):
            data = category_data(index)
            category = categories_by_slug.get(data["slug"])
            if category is None:
                category = Category(**data)
                session.add(category)
            else:
                category.name = data["name"]
            categories.append(category)

        await session.flush()

        products_by_slug = {
            product.slug: product
            for product in (
                await session.scalars(
                    select(Product).where(Product.slug.like("lesson-product-%"))
                )
            ).all()
        }

        for index in range(1, PRODUCT_COUNT + 1):
            category = categories[(index - 1) % CATEGORY_COUNT]
            data = product_data(index, category.id)
            product = products_by_slug.get(data["slug"])
            if product is None:
                session.add(Product(**data))
            else:
                for field, value in data.items():
                    setattr(product, field, value)

        await session.commit()

    print(
        f"Готово: создано/обновлено {CATEGORY_COUNT} категорий "
        f"и {PRODUCT_COUNT} товаров."
    )


if __name__ == "__main__":
    asyncio.run(seed())
