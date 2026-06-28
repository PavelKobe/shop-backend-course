# M03 — PostgreSQL + SQLAlchemy 2.0 (async)

> **Цель:** поднять настоящую базу PostgreSQL в Docker и подключить
> асинхронный ORM с правильным управлением сессиями.

---

## 🟦 Теория

**Реляционная БД** хранит данные в таблицах со строками и столбцами. PostgreSQL —
надёжная, проверенная временем БД, стандарт для backend.

**ORM (Object-Relational Mapping)** позволяет работать с таблицами как с
Python-объектами: вместо ручного SQL ты пишешь `select(Product)`. Мы используем
**SQLAlchemy 2.0** в асинхронном режиме.

Три кита асинхронной работы с БД:

- **Движок (engine)** — `create_async_engine(...)`, держит пул соединений.
- **Сессия (session)** — «рабочая область» для одного запроса: внутри неё ты
  читаешь/пишешь, затем `commit` (сохранить) или `rollback` (откатить).
- **Драйвер `asyncpg`** — асинхронный драйвер PostgreSQL. Отсюда префикс в
  строке подключения: `postgresql+asyncpg://...`.

> **Зачем async?** Пока запрос ждёт ответа от базы, сервер не простаивает, а
> обрабатывает другие запросы. Это и даёт FastAPI высокую производительность.

---

## 🟧 Методология

- **Одна сессия на один HTTP-запрос.** Создаём её в зависимости с `yield`,
  закрываем автоматически после ответа.
- **`async_sessionmaker(expire_on_commit=False)`** — фабрика сессий; флаг не даёт
  SQLAlchemy «протухать» объекты сразу после `commit` (иначе упадёт при попытке
  прочитать поле после сохранения).
- **Соединение с БД — только из настроек** (`Settings.database_url`), не хардкодим.
- **БД поднимаем в Docker**, чтобы у тебя и на втором ПК было одинаковое окружение.

---

## 🟩 Практика

**Шаг 1.** Установи драйвер и ORM:

```bash
pip install "sqlalchemy[asyncio]>=2.0" asyncpg
```

**Шаг 2.** Подними PostgreSQL в Docker — `docker-compose.yml` в корне:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: shop
      POSTGRES_PASSWORD: shop
      POSTGRES_DB: shop
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shop"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

Запусти базу:

```bash
docker compose up -d db
```

Флаг `-d` запускает в фоне. `volumes` сохраняют данные между перезапусками.

**Шаг 3.** Базовый класс моделей — `app/models/base.py`:

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Единая конвенция имён для индексов/ключей — Alembic (M04) скажет спасибо.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
```

**Шаг 4.** Первая модель — `app/models/product.py`:

```python
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(default=None)
```

Это и есть стиль **SQLAlchemy 2.0**: `Mapped[...]` задаёт тип Python,
`mapped_column(...)` — параметры столбца.

**Шаг 5.** Движок, фабрика сессий и зависимость — `app/core/db.py`:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

`get_session` — это **зависимость FastAPI**: эндпоинт пишет
`session: AsyncSession = Depends(get_session)`, получает готовую сессию, а после
ответа она автоматически закрывается.

**Шаг 6.** Проверь подключение — временный эндпоинт в `app/main.py`:

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import products
from app.core.db import get_session

app = FastAPI(title="Shop API", version="0.1.0")
app.include_router(products.router, prefix="/api/v1")


@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
```

Запусти приложение (`uvicorn app.main:app --reload`) и открой
`http://127.0.0.1:8000/health/db`. Ответ `{"db": 1}` означает: приложение
достучалось до PostgreSQL.

> **Частая ошибка.** Если видишь `connection refused` — база ещё не поднялась
> или не совпали логин/пароль/порт со строкой `DATABASE_URL`.

---

> **Итог модуля.** У тебя есть PostgreSQL в Docker, асинхронный движок, первая
> модель `Product` и аккуратная сессия на каждый запрос. Таблицы в базе ещё нет —
> создадим её правильно, через миграции.

**Дальше:** [M04 — Alembic: миграции](M04-alembic.md)
