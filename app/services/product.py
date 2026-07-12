import re

from app.core.cache import cached_json, invalidate
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate


class ProductNotFound(Exception):
    pass


class SlugAlreadyExists(Exception):
    pass


PRODUCT_CACHE_PATTERN = "products:*"


CYRILLIC_TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def make_slug(value: str) -> str:
    value = value.lower().translate(CYRILLIC_TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


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
        slug = make_slug(data.name)
        if not slug:
            slug = "product"
        if await self.repo.get_by_slug(slug):
            raise SlugAlreadyExists
        product = Product(
            name=data.name, slug=slug,
            price=data.price, description=data.description,
        )
        product = await self.repo.add(product)
        await invalidate(PRODUCT_CACHE_PATTERN)
        return product

    async def update(self, product_id: int, data: ProductUpdate) -> Product:
        product = await self.get(product_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self.repo.session.commit()
        await self.repo.session.refresh(product)
        await invalidate(PRODUCT_CACHE_PATTERN)
        return product

    async def delete(self, product_id: int) -> None:
        product = await self.get(product_id)
        await self.repo.delete(product)
        await invalidate(PRODUCT_CACHE_PATTERN)

    async def list_cached(self, skip: int = 0, limit: int = 20):
        key = f"products:list:{skip}:{limit}"

        async def loader():
            products = await self.repo.list(skip, limit)
            return [
                ProductRead.model_validate(product).model_dump(mode="json")
                for product in products
            ]

        return await cached_json(key, ttl=60, loader=loader)
