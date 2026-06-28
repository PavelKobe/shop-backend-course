# M05 — Доменная модель: товары, категории, связи

> **Цель:** спроектировать схему каталога магазина — категории, товары и связь
> между ними — с правильными индексами и внешними ключами.

---

## 🟦 Теория

Реальный каталог — это не одна таблица. Товары делятся на **категории**. Между
ними — **отношение «один-ко-многим»**: одна категория содержит много товаров,
а каждый товар принадлежит одной категории.

Как это выражается в БД:

- У товара есть **внешний ключ (foreign key)** `category_id`, указывающий на
  `categories.id`.
- В ORM это удобно описать через **`relationship`**: тогда у объекта `Category`
  будет список `.products`, а у `Product` — объект `.category`.

Ещё два понятия:

- **Индекс** — ускоряет поиск по столбцу. Ставим на то, по чему часто ищем
  (`name`, `slug`).
- **`slug`** — человекочитаемый идентификатор для URL (`/category/coffee`
  вместо `/category/3`). Должен быть **уникальным**.

---

## 🟧 Методология

- **Внешний ключ + поведение при удалении.** Если удалить категорию, что делать
  с её товарами? Мы запретим удаление, пока есть товары (`ondelete="RESTRICT"`),
  либо обнулим (`SET NULL`). Выбор зависит от бизнес-правила.
- **Индексируй то, по чему ищешь и фильтруешь**, но не подряд всё — индексы
  замедляют запись.
- **`slug` — уникальный индекс.** Двух категорий с одинаковым slug быть не может.
- **Тип `relationship` указывай строкой** (`"Product"`), чтобы избежать проблем с
  порядком импортов.

---

## 🟩 Практика

**Шаг 1.** Категория — `app/models/category.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
    )


from app.models.product import Product  # noqa: E402  (для аннотации выше)
```

**Шаг 2.** Обнови товар, добавив связь с категорией — `app/models/product.py`:

```python
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


from app.models.category import Category  # noqa: E402
```

Что добавилось: `slug`, `stock` (остаток на складе), внешний ключ `category_id`
и двусторонняя связь `category` ↔ `products`.

**Шаг 3.** Зарегистрируй новую модель в Alembic — добавь импорт в `alembic/env.py`:

```python
from app.models.product import Product   # noqa: F401
from app.models.category import Category  # noqa: F401
```

**Шаг 4.** Сгенерируй и примени миграцию:

```bash
alembic revision --autogenerate -m "add categories and product fields"
alembic upgrade head
```

Проверь файл миграции: должна создаваться таблица `categories`, а в `products` —
новые столбцы и внешний ключ.

**Шаг 5.** Наполни базу тестовыми данными (seed) — `scripts/seed.py`:

```python
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
```

Запусти:

```bash
python -m scripts.seed
```

> **Зачем `flush()`?** Он отправляет данные в БД и присваивает `coffee.id`, но не
> завершает транзакцию. Так мы узнаём id категории, чтобы привязать к ней товары,
> и только потом делаем общий `commit`.

---

> **Итог модуля.** Спроектирована реальная схема каталога: категории, товары,
> связь между ними, индексы и slug. В базе уже есть тестовые данные. Теперь
> построим над этим полноценные операции CRUD в чистой архитектуре.

**Дальше:** [M06 — CRUD каталога + слой service/repository](M06-crud-каталог.md)
