from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.datastructures import UploadFile
from starlette.requests import Request

from app.core.db import SessionLocal
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = form["username"], form["password"]
        if isinstance(email, UploadFile) or isinstance(password, UploadFile):
            return False
        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.email == email))
            if (
                user
                and user.is_superuser
                and verify_password(password, user.hashed_password)
            ):
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
