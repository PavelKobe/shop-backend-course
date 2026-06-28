from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/products", tags=["products"])

# Временные данные вместо базы (заменим в M03).
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
