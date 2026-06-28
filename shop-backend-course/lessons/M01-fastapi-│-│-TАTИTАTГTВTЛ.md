# M01 — FastAPI: маршруты, параметры, автодокументация

> **Цель:** научиться описывать эндпоинты, принимать параметры пути и запроса
> и читать автодокументацию.

---

## 🟦 Теория — маршруты и параметры

**Маршрут (route)** — связка «метод + путь → функция». Функция, которая
обрабатывает запрос, называется **обработчиком** (path operation function).

Параметры бывают двух видов:

- **Path-параметры** — часть пути: в `/products/42` число `42` — это id товара.
- **Query-параметры** — после `?`: в `/products?limit=20&q=шуруп` это `limit`
  и `q`.

FastAPI читает аннотации типов в твоей функции и сам: проверяет данные,
приводит типы (строка `"42"` → число `42`), отдаёт понятную ошибку при неверном
вводе и описывает всё это в `/docs`.

> **async def.** Пиши обработчики как `async def` — это «асинхронные» функции.
> Внутри, когда обращаешься к базе или сети, ставишь `await`. Пока данные
> «заглушки», это не критично, но привычку закладываем сразу: позже все
> обращения к БД будут асинхронными.

---

## 🟧 Методология — организация роутов

- **Группируй по домену.** Роуты товаров — в одном файле, пользователей — в
  другом. Связующий объект — `APIRouter`.
- **Версионируй API.** Префикс `/api/v1` позволит выпустить v2 без слома старых
  клиентов.
- **Явные статус-коды и теги.** `status_code=201` при создании,
  `tags=["products"]` — чтобы docs были аккуратно сгруппированы.

---

## 🟩 Практика — каталог-заглушка

**Шаг 1.** Роутер товаров — `app/api/v1/products.py`:

```python
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/products", tags=["products"])

# временные данные вместо базы (заменим в M03)
FAKE = [
    {"id": 1, "name": "Кофемолка", "price": 2990},
    {"id": 2, "name": "Турка", "price": 1490},
]


@router.get("")
async def list_products(
    skip: int = 0,
    limit: int = Query(20, le=100),
    q: str | None = None,
):
    items = FAKE
    if q:
        items = [p for p in items if q.lower() in p["name"].lower()]
    return items[skip : skip + limit]


@router.get("/{product_id}")
async def get_product(product_id: int):
    for p in FAKE:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Товар не найден")
```

**Шаг 2.** Подключи роутер в приложение — `app/main.py`:

```python
from fastapi import FastAPI

from app.api.v1 import products

app = FastAPI(title="Shop API", version="0.1.0")

app.include_router(products.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Шаг 3.** Перезапусти (если не было `--reload`) и проверь в `/docs` или прямо
в браузере:

- `/api/v1/products` — список;
- `/api/v1/products?q=турка` — фильтр по названию;
- `/api/v1/products/1` — один товар;
- `/api/v1/products/999` — увидишь аккуратную ошибку `404`;
- `/api/v1/products/abc` — FastAPI сам вернёт `422`: `abc` не число.

---

> **Итог модуля.** Ты умеешь описывать эндпоинты, принимать path/query-параметры,
> отдавать ошибки и группировать роуты через `APIRouter` с версией `/api/v1`.
> Данные пока ненастоящие — в следующих модулях подключим PostgreSQL.

**Дальше:** [M02 — Pydantic v2: схемы, валидация, настройки](M02-pydantic.md)
