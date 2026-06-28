# M07 — Пользователи и авторизация (JWT)

> **Цель:** реализовать регистрацию, вход, выдачу токена и защиту эндпоинтов,
> включая роли (обычный пользователь и администратор).

---

## 🟦 Теория

**Никогда не храни пароли в открытом виде.** Если базу украдут, утекут все
пароли. Вместо пароля хранят его **хеш** — необратимый «отпечаток». При входе
мы хешируем введённый пароль и сравниваем хеши. Используем алгоритм **bcrypt**,
специально замедленный, чтобы перебор был дорогим.

**JWT (JSON Web Token)** — строка, которую сервер выдаёт после входа. В ней
зашита информация (id пользователя) и подпись секретным ключом. Клиент шлёт этот
токен в заголовке `Authorization: Bearer <token>`, а сервер по подписи понимает:
«токен настоящий, это пользователь №5». Пароль при каждом запросе больше не нужен.

**OAuth2 password flow** — стандартный сценарий: клиент шлёт логин+пароль на
`/auth/login`, получает токен, дальше носит его с собой. FastAPI знает этот
стандарт и красиво показывает кнопку **Authorize** в `/docs`.

---

## 🟧 Методология

- **Секрет и срок жизни токена — в настройках** (`SECRET_KEY`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`), мы уже завели их в M02.
- **Защита эндпоинта — через зависимость** `get_current_user`: она достаёт токен,
  проверяет подпись, находит пользователя.
- **Роли через отдельную зависимость** `get_current_admin`, которая поверх
  проверяет флаг `is_superuser`.
- **Сообщения об ошибке входа — общие** («неверный логин или пароль»), чтобы не
  подсказывать злоумышленнику, какой именно email существует.

---

## 🟩 Практика

**Шаг 1.** Установи библиотеки:

```bash
pip install bcrypt "pyjwt>=2.8"
```

**Шаг 2.** Модель пользователя — `app/models/user.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
```

Зарегистрируй модель в `alembic/env.py` (импорт `User`) и накати миграцию:

```bash
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

**Шаг 3.** Хеширование и JWT — `app/core/security.py`:

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    data = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    return int(data["sub"])
```

**Шаг 4.** Схемы — `app/schemas/user.py`:

```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    is_superuser: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

`EmailStr` требует пакет: `pip install "pydantic[email]"`.

**Шаг 5.** Зависимости авторизации — добавь в `app/api/deps.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    cred_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Не авторизован",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token)
    except Exception:
        raise cred_error
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise cred_error
    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нужны права администратора")
    return user
```

**Шаг 6.** Роуты авторизации — `app/api/v1/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    exists = await session.scalar(select(User).where(User.email == data.email))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email уже зарегистрирован")
    user = User(email=data.email, hashed_password=hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    # OAuth2 присылает поле username — туда кладём email
    user = await session.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user
```

**Шаг 7.** Подключи роутер в `app/main.py`:

```python
from app.api.v1 import auth, products

app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
```

**Шаг 8.** Защити изменение каталога — теперь создавать/менять/удалять товары
может только администратор. В `app/api/v1/products.py` добавь зависимость к
write-операциям:

```python
from app.api.deps import get_current_admin
from app.models.user import User

@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
    _: User = Depends(get_current_admin),   # ← только админ
):
    ...
```

**Проверка в `/docs`:** зарегистрируйся (`/auth/register`), залогинься через
кнопку **Authorize** (введи email и пароль), затем дёрни `/auth/me` — увидишь
свой профиль. Без токена защищённые операции вернут `401`/`403`.

> Чтобы сделать пользователя админом, на первом этапе можно вручную:
> `docker compose exec db psql -U shop -d shop -c "UPDATE users SET is_superuser=true WHERE email='ты@почта';"`
> Позже это удобно делать через админку (M10).

---

> **Итог модуля.** В магазине появились пользователи, безопасное хранение паролей,
> вход с выдачей JWT и защита операций по ролям. Теперь покупатель может не просто
> смотреть каталог, а оформлять заказы.

**Дальше:** [M08 — Корзина и заказы](M08-корзина-заказы.md)
