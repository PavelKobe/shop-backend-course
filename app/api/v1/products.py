from fastapi import APIRouter, HTTPException
from app.schemas.product import ProductRead

router = APIRouter(prefix="/products", tags=["products"])

# Временные данные вместо базы (заменим в M03).
FAKE = [
    {"id": 1, "name": "Кофемолка", "price": 2990},
    {"id": 2, "name": "Турка", "price": 1490},
]


    
@router.get("",response_model=list[ProductRead])
async def filtr_products(
    q: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    sort: str = "id",
    skip: int = 0,
    limit: int = 20,
):
    items = FAKE

    if q:
        items = [p for p in items if q.lower() in p["name"].lower()]

    if min_price is not None:
        items = [p for p in items if p["price"] >= min_price]

    if max_price is not None:
        items = [p for p in items if p["price"] <= max_price]

    if sort == "price_asc":
        items = sorted(items, key=lambda p: p["price"])
    elif sort == "price_desc":
        items = sorted(items, key=lambda p: p["price"], reverse=True)
    elif sort == "name":
        items = sorted(items, key=lambda p: p["name"])

    return items[skip : skip + limit]


@router.get("/{product_id}",response_model=ProductRead)
async def get_product(product_id: int):
    for p in FAKE:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Товар не найден")
