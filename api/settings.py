"""Configuración de la API mediante variables de entorno."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.ecl.config import DATA_DIR, METADATA_PATH, MODEL_PATH, PREDICTIONS_DIR


class Settings(BaseSettings):
    """Ajustes del servicio con valores por defecto derivados del repositorio."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ECL_",
        extra="ignore",
    )

    model_path: Path = MODEL_PATH
    metadata_path: Path = METADATA_PATH
    predictions_dir: Path = PREDICTIONS_DIR
    uploads_dir: Path = DATA_DIR / "uploads"
    cors_origins: str = "http://localhost:3000"
    api_title: str = "ECL API"
    api_version: str = "1.0.0"

    @property
    def cors_origin_list(self) -> list[str]:
        """Devuelve los orígenes CORS configurados como lista."""
        return [
            origen.strip()
            for origen in self.cors_origins.split(",")
            if origen.strip()
        ]


settings = Settings()
