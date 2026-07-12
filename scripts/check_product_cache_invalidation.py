import asyncio
from decimal import Decimal

from app.core.cache import client
from app.core.db import SessionLocal
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product import ProductService, SlugAlreadyExists

CACHE_KEY = "products:list:0:20"
TEMP_PRODUCT_NAME = "Redis cache invalidation test product"


async def cache_exists() -> bool:
    return await client.exists(CACHE_KEY) == 1


async def warm_cache(service: ProductService) -> None:
    await service.list_cached(skip=0, limit=20)


async def main() -> None:
    async with SessionLocal() as session:
        service = ProductService(ProductRepository(session))

        old_product = await service.repo.get_by_slug(
            "redis-cache-invalidation-test-product"
        )
        if old_product is not None:
            await service.repo.delete(old_product)

        await client.delete(CACHE_KEY)
        await warm_cache(service)
        print(f"after_warm_cache={await cache_exists()}")

        try:
            product = await service.create(
                ProductCreate(
                    name=TEMP_PRODUCT_NAME,
                    price=Decimal("123.45"),
                    description="Temporary product for Redis cache test.",
                )
            )
        except SlugAlreadyExists:
            raise RuntimeError("Temporary product slug already exists")

        print(f"after_create_cache_exists={await cache_exists()}")

        await warm_cache(service)
        await service.update(
            product.id,
            ProductUpdate(description="Updated by Redis cache invalidation test."),
        )
        print(f"after_update_cache_exists={await cache_exists()}")

        await warm_cache(service)
        await service.delete(product.id)
        print(f"after_delete_cache_exists={await cache_exists()}")


if __name__ == "__main__":
    asyncio.run(main())
