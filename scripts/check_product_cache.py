import asyncio

from app.core.cache import client
from app.core.db import SessionLocal
from app.repositories.product import ProductRepository
from app.services.product import ProductService


async def main() -> None:
    async with SessionLocal() as session:
        service = ProductService(ProductRepository(session))

        await client.delete("products:list:0:20")
        before = await client.keys("products:*")

        first = await service.list_cached(skip=0, limit=20)
        after_first = await client.keys("products:*")

        second = await service.list_cached(skip=0, limit=20)
        after_second = await client.keys("products:*")

    print(f"before={before}")
    print(f"first_count={len(first)}")
    print(f"after_first={after_first}")
    print(f"second_count={len(second)}")
    print(f"after_second={after_second}")


if __name__ == "__main__":
    asyncio.run(main())
