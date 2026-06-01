from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    API_KEY: str

    OPENROUTER_API_KEY: str
    AI_MODEL: str = "qwen/qwen2.5-3b-instruct"
    AI_MAX_TOKENS: int = 150
    AI_TEMPERATURE: float = 0.3

    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_RETURN_URL: str = ""

    ADMIN_IDS: list[int] = []
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    QUESTIONS_DIR: str = "/app/questions"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list) -> list[int]:
        if isinstance(v, list):
            return [int(x) for x in v]
        return [int(x.strip()) for x in str(v).split(",") if x.strip()]

    @property
    def async_database_url(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


settings = Settings()
