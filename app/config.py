from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Anthropic ────────────────────────────────────────────────────
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "Atelier — Sketch to Pattern"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── File handling ────────────────────────────────────────────────
    max_image_size_mb: int = 10
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/webp"]
    outputs_dir: str = "outputs"

    # ── PDF ──────────────────────────────────────────────────────────
    pdf_template: str = "pattern.html"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()