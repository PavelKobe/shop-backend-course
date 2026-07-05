from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_product_service
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product import (
    ProductNotFound,
    ProductService,
    SlugAlreadyExists,
)

router = APIRouter(prefix="/products", tags=["products"])

# Временные данные вместо базы (заменим в M03).
FAKE = [
    {"id": 1, "name": "Кофемолка", "price": 2990},
    {"id": 2, "name": "Турка", "price": 1490},
]


    
@router.get("", response_model=list[ProductRead])
async def list_products(
    skip: int = 0,
    limit: int = Query(20, le=100),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(skip, limit)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.create(data)
    except SlugAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Товар с таким именем уже есть")


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.get(product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    try:
        return await service.update(product_id, data)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    try:
        await service.delete(product_id)
    except ProductNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
