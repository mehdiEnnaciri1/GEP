"""Réglages de l'application, lus depuis l'environnement (voir `.env.example`)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Reglages(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str
    access_token_minutes: int = 15
    refresh_token_jours: int = 7
    fuseau_horaire: str = "Africa/Casablanca"
    devise: str = "MAD"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int = 5432

    chemin_justificatifs: str = "/donnees/justificatifs"
    taille_max_fichier_mo: int = 5

    @property
    def url_base_donnees(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def obtenir_reglages() -> Reglages:
    return Reglages()  # type: ignore[call-arg]
