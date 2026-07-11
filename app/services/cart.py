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

    async def get_summary(self, user_id: int) -> tuple[list[dict], Decimal]:
        cart = await self._get_or_create_cart(user_id)
        stmt = (
            select(Product, CartItem.quantity)
            .join(CartItem, CartItem.product_id == Product.id)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.id)
        )
        rows = (await self.session.execute(stmt)).all()

        items = [
            {
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "qty": quantity,
            }
            for product, quantity in rows
        ]
        total = sum(
            (item["price"] * item["qty"] for item in items),
            start=Decimal("0"),
        )
        return items, total

    async def remove(self, user_id: int, product_id: int) -> None:
        cart = await self._get_or_create_cart(user_id)
        stmt = select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
        )
        item = await self.session.scalar(stmt)
        if item is not None:
            await self.session.delete(item)
            await self.session.commit()

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
