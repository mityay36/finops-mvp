from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    env: str = "production"
    cors_origins: list[str] = ["*"]

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://finops:finops@localhost:5432/finops",
        description="Async SQLAlchemy DSN, must use postgresql+asyncpg://",
    )
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_default_ttl: int = 300

    # Crypto
    fernet_key: str = Field(
        default="",
        description="32-byte url-safe base64-encoded key. Generate via scripts/generate_fernet_key.py",
    )

    # Scheduler
    scheduler_enabled: bool = True
    billing_sync_interval_minutes: int = 60
    allocations_snapshot_interval_minutes: int = 60
    metrics_snapshot_interval_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
