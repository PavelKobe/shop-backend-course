import asyncio
from decimal import Decimal

from app.core.db import SessionLocal
from app.models.category import Category
from app.models.product import Product


async def seed() -> None:
    async with SessionLocal() as session:
        coffee = Category(name="Кофе", slug="coffee")
        session.add(coffee)
        await session.flush()  # получаем coffee.id, не закрывая транзакцию

        session.add_all([
            Product(name="Кофемолка", slug="grinder",
                    price=Decimal("2990.00"), stock=10, category_id=coffee.id),
            Product(name="Турка", slug="turka",
                    price=Decimal("1490.00"), stock=25, category_id=coffee.id),
        ])
        await session.commit()
    print("Готово: данные добавлены.")


if __name__ == "__main__":
    asyncio.run(seed())