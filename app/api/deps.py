from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_token
from app.models.user import User
from app.repositories.product import ProductRepository
from app.services.product import ProductService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_product_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductService:
    return ProductService(ProductRepository(session))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    cred_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Не авторизован",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token)
    except Exception as err:
        raise cred_error from err
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise cred_error
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нужны права администратора")
    return user
