from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "mysql+pymysql://visual_office:change-me@127.0.0.1:3306/"
        "visual_office_ai?charset=utf8mb4"
    )
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    ai_provider: str = "gemini"
    openrouter_api_key: str = ""
    openrouter_model: str = "minimax/minimax-m3.1-flash:free"
    openrouter_reasoning_enabled: bool = True
    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    workspace_root: str = "../workspace"
    max_instruction_length: int = 4000
    max_output_length: int = 12000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
