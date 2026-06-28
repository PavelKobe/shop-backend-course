# M13 — Тестирование: Pytest

> **Цель:** покрыть код автотестами на отдельной тестовой базе, чтобы менять
> магазин без страха что-то сломать.

---

## 🟦 Теория

Тест — это код, который проверяет другой код. Запустил тесты — увидел, что всё
работает, не открывая браузер. Чем больше тестов, тем спокойнее рефакторинг.

**Пирамида тестов:**

- **Юнит-тесты** (много, быстрые) — проверяют отдельную функцию/сервис.
- **Интеграционные** (средне) — проверяют связку «роут → сервис → БД».
- **E2E** (мало, медленные) — проверяют сценарий целиком.

Инструменты:

- **pytest** — раннер тестов.
- **pytest-asyncio** — позволяет тестировать `async`-функции.
- **httpx.AsyncClient + ASGITransport** — «виртуальный» клиент, который шлёт
  запросы прямо в приложение, без реального сетевого сервера.
- **Фикстуры** — переиспользуемая подготовка (создать тестовую БД, клиента).

> **Главное правило:** тесты идут в отдельную тестовую базу и **не трогают**
> рабочие данные. Каждый тест начинается с чистого листа.

---

## 🟧 Методология

- **Отдельная тестовая БД** — никогда не тестируем на рабочей.
- **Каждый тест независим** — после него данные откатываются.
- **Покрывай в первую очередь бизнес-логику и auth** — там цена ошибки выше.
- **Имя теста описывает проверку:** `test_create_product_requires_admin`.

---

## 🟩 Практика

**Шаг 1.** Установи и добавь тестовую БД в `docker-compose.yml`:

```bash
pip install pytest pytest-asyncio httpx "aiosqlite"
```

Для тестов удобно поднять отдельную базу (или использовать SQLite в памяти для
скорости). Здесь покажем изолированную PostgreSQL-базу для тестов:

```yaml
  test-db:
    image: postgres:16
    environment:
      POSTGRES_USER: shop
      POSTGRES_PASSWORD: shop
      POSTGRES_DB: shop_test
    ports:
      - "5433:5432"
```

**Шаг 2.** Конфигурация pytest — `pyproject.toml` (создадим его полнее в M14):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Шаг 3.** Фикстуры — `tests/conftest.py`:

```python
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import get_session
from app.main import app
from app.models.base import Base

TEST_URL = "postgresql+asyncpg://shop:shop@localhost:5433/shop_test"

engine = create_async_engine(TEST_URL)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def prepare_db() -> AsyncGenerator[None, None]:
    # создаём схему перед тестом, сносим после — чистый лист каждый раз
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

`dependency_overrides` — мощный приём FastAPI: подменяем зависимость `get_session`
на тестовую, и всё приложение незаметно ходит в тестовую базу.

**Шаг 4.** Тест авторизации и сценария заказа — `tests/test_orders.py`:

```python
async def test_register_login_and_me(client):
    r = await client.post("/api/v1/auth/register",
                          json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 201

    r = await client.post("/api/v1/auth/login",
                          data={"username": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/api/v1/auth/me",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


async def test_login_with_wrong_password(client):
    await client.post("/api/v1/auth/register",
                      json={"email": "x@y.com", "password": "secret123"})
    r = await client.post("/api/v1/auth/login",
                          data={"username": "x@y.com", "password": "WRONG"})
    assert r.status_code == 401
```

**Шаг 5.** Тест прав на каталог — `tests/test_products.py`:

```python
async def test_create_product_requires_auth(client):
    r = await client.post("/api/v1/products",
                          json={"name": "Чайник", "price": "1990.00"})
    assert r.status_code == 401  # без токена нельзя
```

**Шаг 6.** Запусти тесты (тестовая база должна быть поднята):

```bash
docker compose up -d test-db
pytest -v
```

Зелёные галочки означают: магазин работает как задумано. Добавь отчёт покрытия:

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

> **Итог модуля.** У магазина есть автотесты на изолированной базе: регистрация,
> вход, права доступа. Теперь можно смело менять код — тесты подстрахуют. Дальше
> наведём порядок в самом коде автоматически.

**Дальше:** [M14 — Качество кода: Ruff, Mypy, pre-commit](M14-ruff-mypy-precommit.md)
