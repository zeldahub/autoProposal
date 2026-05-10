"""Pydantic settings — .env 로딩."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_port: int = 8080
    app_base_url: str = "http://localhost:8080"
    app_cors_origins: str = "http://localhost:5173"

    mariadb_url: str = "mysql+pymysql://lon_app:CHANGE_ME_LON_2026@127.0.0.1:3306/lon?charset=utf8mb4"
    mongo_url: str = "mongodb://lon_app:CHANGE_ME_LON_2026@127.0.0.1:27017/lon?authSource=lon"

    jwt_secret: str = Field(default="dev-only-not-for-prod-32chars-please")
    aes_master_key_b64: str = Field(default="")

    workspace_dir: str = "D:/github/autoProposal/workspace"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # 잡 설정
    jobs_enabled: bool = True
    attachment_ttl_hours: int = 24
    attachment_cleanup_interval_min: int = 60
    mongo_repair_interval_min: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
