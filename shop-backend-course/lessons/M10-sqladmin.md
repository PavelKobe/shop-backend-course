# M10 — SQLAdmin: админка

> **Цель:** поднять админ-панель для управления каталогом, пользователями и
> заказами — без ручных SQL-запросов.

---

## 🟦 Теория

Админу нужно добавлять товары, менять цены, смотреть заказы. Писать для этого
отдельный интерфейс долго. **SQLAdmin** генерирует готовую веб-админку прямо из
твоих моделей SQLAlchemy: список записей, формы создания и редактирования,
удаление — всё «из коробки».

Главное понятие — **`ModelView`**: класс, который говорит админке «покажи вот
эту модель, вот эти колонки в списке, вот эти поля в форме».

Админку обязательно **защищают авторизацией** — иначе любой откроет её и удалит
все товары. SQLAdmin позволяет подключить свой `AuthenticationBackend`.

---

## 🟧 Методология

- **Показывай в списках только нужные колонки** — длинные описания и пароли не
  выводим.
- **Защити вход в админку** — переиспользуем логин/JWT из M07.
- **Не показывай `hashed_password`** в форме пользователя.
- **Админка — отдельный модуль** (`app/admin/`), не мешаем её с API.

---

## 🟩 Практика

**Шаг 1.** Установи:

```bash
pip install sqladmin
```

**Шаг 2.** Бэкенд аутентификации админки — `app/admin/auth.py`:

```python
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.core.db import SessionLocal
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = form["username"], form["password"]
        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.email == email))
            if user and user.is_superuser and verify_password(password, user.hashed_password):
                request.session["token"] = create_access_token(user.id)
                return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        try:
            decode_token(token)
            return True
        except Exception:
            return False
```

**Шаг 3.** Описания моделей — `app/admin/views.py`:

```python
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
```

**Шаг 4.** Подключи админку в `app/main.py`:

```python
from sqladmin import Admin

from app.admin.auth import AdminAuth
from app.admin.views import (
    CategoryAdmin, OrderAdmin, OrderItemAdmin, ProductAdmin, UserAdmin,
)
from app.core.config import get_settings
from app.core.db import engine

admin = Admin(
    app,
    engine,
    authentication_backend=AdminAuth(secret_key=get_settings().secret_key),
)
for view in (ProductAdmin, CategoryAdmin, UserAdmin, OrderAdmin, OrderItemAdmin):
    admin.add_view(view)
```

**Шаг 5.** Открой `http://127.0.0.1:8000/admin`. Войди под пользователем с
`is_superuser=true` (как сделать админом — см. конец M07). Внутри можно добавлять
товары и категории, смотреть пользователей и заказы.

> Теперь наполнять каталог можно мышкой через админку — это и проще, и нагляднее,
> чем сид-скрипт.

---

> **Итог модуля.** У магазина есть защищённая админка: товары, категории,
> пользователи и заказы управляются через веб-интерфейс. Базовый функционал
> магазина полностью собран. Дальше — ускорение и инфраструктура.

**Дальше:** [M11 — Redis: кэширование](M11-redis-кэш.md)
