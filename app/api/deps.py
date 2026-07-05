from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.product import ProductRepository
from app.services.product import ProductService


def get_product_service(
    session: AsyncSession = Depends(get_session),
) -> ProductService:
    return ProductService(ProductRepository(session))

