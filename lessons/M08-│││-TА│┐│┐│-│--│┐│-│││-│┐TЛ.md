# M08 — Корзина и заказы

> **Цель:** реализовать ядро магазина — корзину и оформление заказа, причём
> оформление выполнить в транзакции, чтобы данные не «разъехались».

---

## 🟦 Теория

Покупка состоит из двух стадий:

1. **Корзина** — временный список того, что пользователь хочет купить.
2. **Заказ** — зафиксированная покупка: позиции, количество, цены, статус.

Модель данных:

- `Cart` (корзина пользователя) → много `CartItem` (товар + количество).
- `Order` (заказ) → много `OrderItem`. В `OrderItem` мы **копируем цену** на
  момент покупки — потому что цена товара в каталоге потом может измениться, а в
  заказе она должна остаться прежней.

**Транзакция** — группа операций «всё или ничего». При оформлении заказа мы:
создаём `Order`, переносим позиции, списываем остатки со склада, очищаем корзину.
Если на любом шаге сбой — откатывается всё, и база остаётся целостной. Иначе мог
бы появиться заказ без позиций или списанный товар без заказа.

---

## 🟧 Методология

- **Цену фиксируй в заказе** (`OrderItem.price`), не ссылайся на текущую.
- **Проверяй наличие** (`stock`) перед оформлением.
- **Всё оформление — в одной транзакции** (`async with session.begin()`).
- **Заказ привязан к пользователю** — берём его из `get_current_user`.
- **Статусы заказа** — перечисление (`new`, `paid`, `shipped`, `cancelled`).

---

## 🟩 Практика

**Шаг 1.** Модели — `app/models/order.py`:

```python
import enum
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrderStatus(str, enum.Enum):
    new = "new"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    cart: Mapped["Cart"] = relationship(back_populates="items")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        String(20), default=OrderStatus.new
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # цена на момент покупки
    order: Mapped["Order"] = relationship(back_populates="items")
```

Зарегистрируй модели в `alembic/env.py` и накати миграцию:

```bash
alembic revision --autogenerate -m "add carts and orders"
alembic upgrade head
```

**Шаг 2.** Схемы — `app/schemas/order.py`:

```python
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AddToCart(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    quantity: int
    price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    total: Decimal
    items: list[OrderItemRead]
```

**Шаг 3.** Сервис корзины и оформления — `app/services/cart.py`:

```python
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Cart, CartItem, Order, OrderItem, OrderStatus
from app.models.product import Product


class CartService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_or_create_cart(self, user_id: int) -> Cart:
        stmt = (
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items))
        )
        cart = await self.session.scalar(stmt)
        if cart is None:
            cart = Cart(user_id=user_id)
            self.session.add(cart)
            await self.session.commit()
            await self.session.refresh(cart)
        return cart

    async def add(self, user_id: int, product_id: int, quantity: int) -> Cart:
        product = await self.session.get(Product, product_id)
        if product is None:
            raise ValueError("Товар не найден")
        cart = await self._get_or_create_cart(user_id)
        for item in cart.items:
            if item.product_id == product_id:
                item.quantity += quantity
                break
        else:
            self.session.add(
                CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
            )
        await self.session.commit()
        return await self._get_or_create_cart(user_id)

    async def checkout(self, user_id: int) -> Order:
        cart = await self._get_or_create_cart(user_id)
        if not cart.items:
            raise ValueError("Корзина пуста")

        # вся операция — в одной транзакции
        async with self.session.begin_nested():
            order = Order(user_id=user_id, status=OrderStatus.new, total=Decimal("0"))
            self.session.add(order)
            await self.session.flush()

            total = Decimal("0")
            for item in cart.items:
                product = await self.session.get(Product, item.product_id)
                if product is None or product.stock < item.quantity:
                    raise ValueError(f"Недостаточно товара: {item.product_id}")
                product.stock -= item.quantity
                self.session.add(OrderItem(
                    order_id=order.id, product_id=product.id,
                    quantity=item.quantity, price=product.price,
                ))
                total += product.price * item.quantity

            order.total = total
            # очищаем корзину
            for item in list(cart.items):
                await self.session.delete(item)

        await self.session.commit()
        await self.session.refresh(order, attribute_names=["items"])
        return order
```

> `begin_nested()` создаёт точку отката внутри транзакции; если внутри будет
> исключение, изменения этого блока откатятся, а целостность сохранится.

**Шаг 4.** Роуты — `app/api/v1/cart.py`:

```python
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
```

Подключи роутер в `app/main.py` (`app.include_router(cart.router, prefix="/api/v1")`).

**Проверка:** залогинься, добавь товар в корзину (`POST /cart/items`), оформи
заказ (`POST /cart/checkout`). В ответе придёт заказ с позициями и суммой, остаток
товара уменьшится, корзина очистится.

---

> **Итог модуля.** Готово ядро магазина: корзина и атомарное оформление заказа со
> списанием остатков и фиксацией цен. Backend уже умеет всё главное. Теперь дадим
> покупателю человеческий интерфейс — HTML-страницы.

**Дальше:** [M09 — Jinja2-витрина (шаблоны готовы)](M09-jinja2-витрина.md)
