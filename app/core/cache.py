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