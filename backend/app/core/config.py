"""Application configuration via Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings

# Locate project root (core/config.py -> app -> backend -> repository root).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # App
    app_name: str = "Customer Service Agent"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ws_heartbeat_interval: int = 30

    # LLM (OpenAI-compatible)
    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model: str = "qwen-max"
    llm_fast_model: str = "qwen-max"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # Database
    database_url: str = "postgresql+asyncpg://cs_admin:cs_secret_2024@localhost:5432/customer_service"
    database_url_sync: str = "postgresql://cs_admin:cs_secret_2024@localhost:5432/customer_service"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Embedding
    embedding_api_key: str = ""
    embedding_api_base: str = ""
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
