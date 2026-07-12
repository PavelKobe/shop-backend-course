from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")
    app_name: str = "Shop API"
    database_url: str = "postgresql+asyncpg://shop:shop@localhost:5432/shop"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 60

@lru_cache
def get_settings()-> Settings:
    return Settings()
