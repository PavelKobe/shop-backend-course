from fastapi import FastAPI

from app.api.v1 import products
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import products
from app.core.db import get_session

app = FastAPI(title="Shop API", version="0.1.0")

app.include_router(products.router, prefix="/api/v1")


#@app.get("/health")
#async def health():
    #return {"status": "ok"}

@app.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
