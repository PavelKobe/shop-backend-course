from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models.user import User
from app.schemas.order import AddToCart, OrderRead
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["cart"])

def get_cart_service(session=Depends(get_session)) -> CartService:
    return CartService(session)


@router.post("/items")
async def add_to_cart(
    data: AddToCart,
    user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    try:
        cart = await service.add(user.id, data.product_id, data.quantity)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"items": [{"product_id": i.product_id, "quantity": i.quantity}
                      for i in cart.items]}


@router.post("/checkout", response_model=OrderRead)
async def checkout(
    user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    try:
        return await service.checkout(user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))