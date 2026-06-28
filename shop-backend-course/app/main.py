from fastapi import FastAPI

from app.api.v1 import products

app = FastAPI(title="Shop API", version="0.1.0")

app.include_router(products.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
