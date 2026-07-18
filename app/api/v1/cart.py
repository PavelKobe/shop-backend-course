from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models.user import User
from app.schemas.order import AddToCart, OrderRead
from app.services.cart import CartService
from app.tasks.email import send_order_email

router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartService:
    return CartService(session)


@router.post("/items")
async def add_to_cart(
    data: AddToCart,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        cart = await service.add(user.id, data.product_id, data.quantity)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err
    return {
        "items": [
            {"product_id": i.product_id, "quantity": i.quantity} for i in cart.items
        ]
    }


@router.post("/checkout", response_model=OrderRead)
async def checkout(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    try:
        order = await service.checkout(user.id)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err
    # .delay() ставит задачу в очередь и сразу возвращает управление
    send_order_email.delay(order.id, user.email)
    return order
