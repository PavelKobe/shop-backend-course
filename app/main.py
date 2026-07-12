from fastapi import FastAPI

from app.api.v1 import products
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import products,auth,cart
from app.core.db import get_session
from fastapi.staticfiles import StaticFiles
from app.web import views
from sqladmin import Admin

from app.admin.auth import AdminAuth
from app.admin.views import (
    CategoryAdmin, OrderAdmin, OrderItemAdmin, ProductAdmin, UserAdmin,
)
from app.core.config import get_settings
from app.core.db import engine

app = FastAPI(title="Shop API", version="0.1.0")

admin = Admin(
    app,
    engine,
    authentication_backend=AdminAuth(secret_key=get_settings().secret_key),
)
for view in (ProductAdmin, CategoryAdmin, UserAdmin, OrderAdmin, OrderItemAdmin):
    admin.add_view(view)

app.include_router(products.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(views.router)
#@app.get("/health")
#async def health():
    #return {"status": "ok"}

@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
