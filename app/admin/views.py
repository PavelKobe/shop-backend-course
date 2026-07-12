from sqladmin import ModelView

from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

class ProductAdmin(ModelView, model=Product):
    column_list = [Product.id, Product.name, Product.price, Product.stock]
    column_searchable_list = [Product.name]
    name = "Товар"
    name_plural = "Товары"


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.slug]
    name_plural = "Категории"


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.is_superuser, User.is_active]
    column_details_exclude_list = [User.hashed_password]  # не светим хеш
    name_plural = "Пользователи"


class OrderAdmin(ModelView, model=Order):
    column_list = [Order.id, Order.user_id, Order.status, Order.total]
    name_plural = "Заказы"


class OrderItemAdmin(ModelView, model=OrderItem):
    column_list = [OrderItem.id, OrderItem.order_id, OrderItem.product_id,
                   OrderItem.quantity, OrderItem.price]
    name_plural = "Позиции заказов"