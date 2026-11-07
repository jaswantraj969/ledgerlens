"""Application settings, read from the environment."""

from pathlib import Path
from typing import Literal

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
    # Worker. "rules" needs no model. "llm" fails a job when the model is unavailable.
    # "llm_or_rules" degrades to rules and records why on the extraction run.
    extraction_mode: Literal["rules", "llm", "llm_or_rules"] = "rules"
    schema_name: str = "default"
    llm_model: str = "llama3.2:3b"
    llm_prompt: str = "1.0"
    ollama_url: str = "http://127.0.0.1:11434"
    llm_timeout_seconds: float = 300.0
    llm_cache_dir: Path = Path("var/llm-cache")
    job_retry_intervals: list[int] = [10, 60, 300]
    job_timeout_seconds: int = 900
