from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_product_service
from app.api.v1.cart import get_cart_service
from app.services.cart import CartService
from app.services.product import ProductNotFound, ProductService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="frontend/templates")

# Пока у витрины нет входа через браузер, используем учебного пользователя.
# Его запись с id=1 должна существовать в таблице users.
DEMO_USER_ID = 1


@router.get("/", response_class=HTMLResponse)
async def shop_index(
    request: Request,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    products = await service.list(limit=100)
    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={"products": products},
    )


@router.get("/p/{product_id}", response_class=HTMLResponse)
async def product_page(
    product_id: int,
    request: Request,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    try:
        product = await service.get(product_id)
    except ProductNotFound:
        return templates.TemplateResponse(
            request=request,
            name="products.html",
            context={"products": []},
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="product.html",
        context={"product": product},
    )


@router.post("/cart/add/{product_id}")
async def add_product_to_cart(
    product_id: int,
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    await cart_service.add(DEMO_USER_ID, product_id, quantity=1)
    return RedirectResponse(url="/cart", status_code=303)


@router.post("/cart/remove/{product_id}")
async def remove_product_from_cart(
    product_id: int,
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    await cart_service.remove(DEMO_USER_ID, product_id)
    return RedirectResponse(url="/cart", status_code=303)


@router.get("/cart", response_class=HTMLResponse)
async def cart_page(
    request: Request,
    cart_service: Annotated[CartService, Depends(get_cart_service)],
):
    items, total = await cart_service.get_summary(DEMO_USER_ID)
    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context={"items": items, "total": total},
    )
