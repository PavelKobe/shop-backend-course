from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from slugify import slugify
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