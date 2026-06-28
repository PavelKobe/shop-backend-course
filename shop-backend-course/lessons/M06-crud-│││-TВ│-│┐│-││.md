# M06 — CRUD каталога + слой service/repository

> **Цель:** сделать полноценные операции с каталогом (создать/прочитать/
> изменить/удалить) в чистой слоистой архитектуре, а не сваливая всё в роут.

---

## 🟦 Теория

**CRUD** — четыре базовые операции: Create, Read, Update, Delete. Можно написать
их прямо в эндпоинте, но в больших проектах это превращается в кашу. Профи
разделяют код на **слои**:

```
HTTP-запрос
   │
   ▼
[ Router ]   — принимает запрос, валидирует, формирует ответ
   │
   ▼
[ Service ]  — бизнес-логика и правила («товар с таким slug уже есть»)
   │
   ▼
[ Repository ] — запросы к БД (select / insert / update / delete)
   │
   ▼
PostgreSQL
```

Каждый слой знает только о соседе снизу. Роут не пишет SQL, репозиторий не знает
про HTTP. Это делает код понятным и тестируемым (в M13 увидишь, как удобно
тестировать сервис отдельно).

**Пагинация** — отдаём не все товары сразу, а порциями: `limit` (сколько) и
`offset` (с какого).

---

## 🟧 Методология

- **Роут не лезет в БД напрямую** — только через сервис.
- **Запросы к БД — в репозитории**, бизнес-правила — в сервисе.
- **Правильные статус-коды:** `201` при создании, `204` при удалении (без тела),
  `404` если не найдено.
- **Не доверяй клиенту `limit`** — ограничивай сверху (`le=100`), иначе он
  попросит миллион строк.

---

## 🟩 Практика

**Шаг 1.** Репозиторий — `app/repositories/product.py`:

```python
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
```

**Шаг 2.** Сервис — `app/services/product.py`:

```python
from slugify import slugify  # pip install python-slugify

from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductNotFound(Exception):
    pass


class SlugAlreadyExists(Exception):
    pass


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self.repo = repo

    async def list(self, skip: int = 0, limit: int = 20):
        return await self.repo.list(skip, limit)

    async def get(self, product_id: int) -> Product:
        product = await self.repo.get(product_id)
        if product is None:
            raise ProductNotFound
        return product

    async def create(self, data: ProductCreate) -> Product:
        slug = slugify(data.name)
        if await self.repo.get_by_slug(slug):
            raise SlugAlreadyExists
        product = Product(
            name=data.name, slug=slug,
            price=data.price, description=data.description,
        )
        return await self.repo.add(product)

    async def update(self, product_id: int, data: ProductUpdate) -> Product:
        product = await self.get(product_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self.repo.session.commit()
        await self.repo.session.refresh(product)
        return product

    async def delete(self, product_id: int) -> None:
        product = await self.get(product_id)
        await self.repo.delete(product)
```

`model_dump(exclude_unset=True)` берёт только реально переданные поля — это и есть
смысл `Update`-схемы с необязательными полями.

**Шаг 3.** Зависимость, собирающая сервис — `app/api/deps.py`:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.product import ProductRepository
from app.services.product import ProductService


def get_product_service(
    session: AsyncSession = Depends(get_session),
) -> ProductService:
    return ProductService(ProductRepository(session))
```

**Шаг 4.** Роуты — `app/api/v1/products.py` (теперь работает с реальной БД):

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_product_service
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import (
    ProductNotFound,
    ProductService,
    SlugAlreadyExists,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
async def list_products(
    skip: int = 0,
    limit: int = Query(20, le=100),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(skip, limit)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.create(data)
    except SlugAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Товар с таким именем уже есть")


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.get(product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.update(product_id, data)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    try:
        await service.delete(product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
```

**Шаг 5.** Установи зависимость для slug и проверь в `/docs`:

```bash
pip install python-slugify
```

Создай товар через `POST /api/v1/products`, получи список, измени `PATCH`, удали
`DELETE`. Категории делаются по тому же шаблону (повтори слои для `Category` —
отличная самостоятельная практика).

---

> **Итог модуля.** Каталог получил полноценный CRUD в чистой архитектуре
> router → service → repository, с пагинацией и корректными статус-кодами. Этот
> же шаблон мы переиспользуем для пользователей и заказов.

**Дальше:** [M07 — Пользователи и авторизация (JWT)](M07-авторизация-jwt.md)
