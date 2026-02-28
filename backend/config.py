from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production"
    DATABASE_URL: str = "sqlite+aiosqlite:///./ssl_monitor.db"
    TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str = "http://localhost:5173"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # 证书检测超时（秒）
    CHECK_TIMEOUT: int = 10
    # APScheduler：每天几点执行（UTC）
    DAILY_CHECK_HOUR: int = 1

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
