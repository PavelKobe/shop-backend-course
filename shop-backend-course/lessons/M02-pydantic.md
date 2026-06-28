# M02 — Pydantic v2: схемы, валидация, настройки

> **Цель:** научиться строго описывать данные — отдельные схемы для входа и
> выхода — и вынести конфигурацию приложения в `.env`.

---

## 🟦 Теория — зачем нужны схемы

В M01 наши эндпоинты принимали и возвращали «сырые» словари. Это опасно: никто
не проверяет, что цена — число, а название — не пустое. **Pydantic** решает это:
ты описываешь форму данных классом, а Pydantic проверяет и приводит типы.

Важно различать два разных понятия (новички их путают):

- **Модель БД** (SQLAlchemy, появится в M03) — описывает таблицу в базе.
- **Схема** (Pydantic) — описывает данные на границе API: что приходит в запросе
  и что уходит в ответе.

Для одной сущности «товар» обычно нужно **несколько** схем:

| Схема | Когда | Особенность |
|-------|-------|-------------|
| `ProductCreate` | приходит при создании | без `id` — его выдаёт база |
| `ProductUpdate` | приходит при изменении | все поля необязательные |
| `ProductRead` | уходит в ответе | есть `id`, читается из объекта БД |

> **Почему нельзя возвращать модель БД напрямую?** Потому что в ней могут быть
> поля, которые нельзя показывать (например `hashed_password` у пользователя).
> Ответ всегда идёт через `Read`-схему — она как «фильтр на выходе».

---

## 🟧 Методология

- **Разделяй схемы по назначению:** `Create` / `Update` / `Read`. Не пытайся
  обойтись одной «на всё».
- **`Update` — все поля `| None = None`,** чтобы можно было менять только часть.
- **Никогда не клади секреты в код.** `SECRET_KEY`, пароль от базы — только в
  `.env`, а `.env` уже в `.gitignore` (мы добавили его в M00).
- **Конфигурацию читай через `pydantic-settings`** — она сама подтянет
  переменные окружения и проверит их типы.

---

## 🟩 Практика

**Шаг 1.** Установи зависимости (добавим в `requirements.txt`):

```bash
pip install "pydantic-settings>=2.0"
```

**Шаг 2.** Схемы товара — `app/schemas/product.py`:

```python
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    price: Decimal | None = Field(default=None, gt=0)
    description: str | None = None


class ProductRead(BaseModel):
    # from_attributes=True позволяет создать схему прямо из объекта SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    description: str | None = None
```

Разбор:

- `Field(gt=0)` — цена строго больше нуля; `min_length=1` — имя не пустое.
- `Decimal` вместо `float` — **деньги нельзя хранить во float** (ошибки
  округления). Цена в копейках/центах хранилась бы как `Numeric` в БД.
- `from_attributes=True` (в Pydantic v2) — разрешает собрать `ProductRead` из
  объекта SQLAlchemy: `ProductRead.model_validate(product_obj)`.

**Шаг 3.** Конфигурация — `app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Shop API"
    # значения по умолчанию подходят для docker-compose из M03
    database_url: str = "postgresql+asyncpg://shop:shop@localhost:5432/shop"
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`@lru_cache` гарантирует, что настройки прочитаются из `.env` один раз и потом
переиспользуются.

**Шаг 4.** Сам `.env` в корне проекта (он не попадёт в git):

```dotenv
DATABASE_URL=postgresql+asyncpg://shop:shop@localhost:5432/shop
SECRET_KEY=поставь-сюда-длинную-случайную-строку
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Шаг 5.** Подключи схемы к эндпоинтам из M01 — `app/api/v1/products.py`:

```python
from fastapi import APIRouter, HTTPException, Query

from app.schemas.product import ProductRead

router = APIRouter(prefix="/products", tags=["products"])

FAKE = [
    {"id": 1, "name": "Кофемолка", "price": 2990, "description": None},
    {"id": 2, "name": "Турка", "price": 1490, "description": None},
]


@router.get("", response_model=list[ProductRead])
async def list_products(skip: int = 0, limit: int = Query(20, le=100)):
    return FAKE[skip : skip + limit]


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int):
    for p in FAKE:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Товар не найден")
```

Теперь `response_model=ProductRead` гарантирует форму ответа и автоматически
описывает её в `/docs`. Открой Swagger — у схем появились типы и ограничения.

---

> **Итог модуля.** Данные на границе API стали строгими: отдельные схемы для
> создания, изменения и чтения; конфигурация и секреты вынесены в `.env` и
> читаются типобезопасно. Готова почва, чтобы подключить настоящую базу.

**Дальше:** [M03 — PostgreSQL + SQLAlchemy 2.0 (async)](M03-postgresql-sqlalchemy.md)
