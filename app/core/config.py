"""Application-wide settings loaded from environment / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # SQLite
    db_path: str = "pixlpal.db"

    # Server
    cors_origins: list[str] = ["*"]
    debug: bool = False

    @property
    def db_file(self) -> Path:
        """Resolved absolute path to the SQLite database file."""
        return Path(self.db_path).resolve()


settings = Settings()
