"""Application settings, read from the environment."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEDGERLENS_", extra="ignore")

    database_url: str
    redis_url: str
    jwt_secret: SecretStr
    storage_dir: Path = Path("var/storage")
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pages: int = 50
    auth_rate_limit: int = 10
    upload_rate_limit: int = 60
    rate_window_seconds: int = 60
    queue_name: str = "ledgerlens"
