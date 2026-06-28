# M11 — Redis: кэширование

> **Цель:** ускорить каталог с помощью кэша в Redis и понять, когда и как
> сбрасывать кэш, чтобы пользователь не видел устаревших данных.

---

## 🟦 Теория

Каждый запрос к каталогу идёт в PostgreSQL. Но каталог меняется редко, а читают
его часто. **Кэш** — это быстрое хранилище, куда мы кладём готовый ответ и отдаём
его без обращения к базе.

**Redis** — сверхбыстрое хранилище «ключ-значение» в оперативной памяти. Идеален
для кэша. Ключевые понятия:

- **TTL (time to live)** — срок жизни записи в кэше. Через N секунд Redis сам её
  удалит, и следующий запрос снова сходит в базу.
- **Инвалидация** — принудительный сброс кэша, когда данные изменились (добавили
  товар). Это самая каверзная часть: «в программировании две сложные вещи —
  инвалидация кэша и придумывание имён».

Схема работы (cache-aside):

```
запрос → есть в Redis? ──да──> отдать из кэша (быстро)
                       └─нет─> сходить в БД → положить в Redis с TTL → отдать
```

---

## 🟧 Методология

- **Кэшируй «горячее и редко меняющееся»** — список товаров, категории.
- **Ставь TTL** — даже если забудешь сбросить кэш, он протухнет сам.
- **Сбрасывай кэш при изменении** товара (create/update/delete).
- **Ключи делай осмысленными:** `products:list:skip=0:limit=20`.
- **Redis поднимаем в Docker** — рядом с базой.

---

## 🟩 Практика

**Шаг 1.** Установи клиент и добавь Redis в `docker-compose.yml`:

```bash
pip install "redis>=5.0"
```

```yaml
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

Добавь в `app/core/config.py`:

```python
    redis_url: str = "redis://localhost:6379/0"
```

**Шаг 2.** Подключение к Redis — `app/core/cache.py`:

```python
import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()
client = redis.from_url(settings.redis_url, decode_responses=True)


async def cached_json(
    key: str,
    ttl: int,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Вернуть из кэша или вычислить через loader и закэшировать."""
    raw = await client.get(key)
    if raw is not None:
        return json.loads(raw)
    value = await loader()
    await client.set(key, json.dumps(value, default=str), ex=ttl)
    return value


async def invalidate(pattern: str) -> None:
    """Удалить все ключи по шаблону, напр. 'products:*'."""
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)
```

**Шаг 3.** Закэшируй список товаров в сервисе — обнови `app/services/product.py`:

```python
from app.core.cache import cached_json, invalidate
from app.schemas.product import ProductRead


class ProductService:
    # ... (методы из M06)

    async def list_cached(self, skip: int = 0, limit: int = 20):
        key = f"products:list:{skip}:{limit}"

        async def loader():
            products = await self.repo.list(skip, limit)
            return [ProductRead.model_validate(p).model_dump() for p in products]

        return await cached_json(key, ttl=60, loader=loader)

    async def create(self, data):
        product = await super_create(self, data)  # логика создания из M06
        await invalidate("products:*")            # сбрасываем кэш
        return product
```

> На практике вызов `invalidate("products:*")` нужно добавить во все методы,
> меняющие товары: `create`, `update`, `delete`. После любого изменения список
> пересоберётся из базы при следующем запросе.

**Шаг 4.** Используй кэш в роуте списка — в `app/api/v1/products.py` поменяй
`list_products` на `await service.list_cached(skip, limit)`.

**Шаг 5.** Проверь эффект. Запусти Redis (`docker compose up -d redis`), сделай
два одинаковых запроса к `/api/v1/products`. Первый сходит в базу, второй
вернётся из кэша заметно быстрее. Посмотреть ключи можно так:

```bash
docker compose exec redis redis-cli keys "products:*"
```

После создания товара ключи исчезнут (инвалидация) и появятся заново при чтении.

---

> **Итог модуля.** Каталог ускорен кэшем с TTL и корректной инвалидацией при
> изменениях. Redis уже работает в нашей инфраструктуре — он же пригодится как
> хранилище результатов фоновых задач в следующем модуле.

**Дальше:** [M12 — Celery + RabbitMQ: фоновые задачи](M12-celery-rabbitmq.md)
