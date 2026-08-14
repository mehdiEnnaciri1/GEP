"""Fixtures partagées aux tests e2e (endpoints via httpx, sur une vraie base).

Un vrai Postgres (testcontainers), migré une fois par session de tests. Chaque
test reçoit une session et un client HTTP propres ; les tables sont vidées
après chaque test pour l'isolation (les endpoints commitent eux-mêmes, un
simple rollback ne suffirait pas).

Volontairement dans `tests/e2e/`, pas à la racine de `tests/` : un conftest
racine avec cette fixture en `autouse` ferait démarrer un conteneur Postgres
même pour les tests unitaires purs de `tests/unit/`, qui n'en ont pas besoin.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

from alembic import command

_RACINE_BACKEND = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def _conteneur_postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16") as conteneur:
        yield conteneur


@pytest.fixture(scope="session")
def _url_asyncpg(_conteneur_postgres: PostgresContainer) -> str:
    return (
        f"postgresql+asyncpg://{_conteneur_postgres.username}:{_conteneur_postgres.password}"
        f"@{_conteneur_postgres.get_container_host_ip()}"
        f":{_conteneur_postgres.get_exposed_port(5432)}/{_conteneur_postgres.dbname}"
    )


@pytest.fixture(scope="session", autouse=True)
def _migrer_base_test(_conteneur_postgres: PostgresContainer) -> None:
    """Pointe les réglages de l'appli sur le conteneur de test, puis joue les
    migrations Alembic — une fois pour toute la session de tests."""

    os.environ["POSTGRES_HOST"] = _conteneur_postgres.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(_conteneur_postgres.get_exposed_port(5432))
    os.environ["POSTGRES_USER"] = _conteneur_postgres.username
    os.environ["POSTGRES_PASSWORD"] = _conteneur_postgres.password
    os.environ["POSTGRES_DB"] = _conteneur_postgres.dbname
    os.environ.setdefault("SECRET_KEY", "cle-de-test-jamais-utilisee-en-production")

    from app.core.config import obtenir_reglages

    obtenir_reglages.cache_clear()

    config = Config(str(_RACINE_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(_RACINE_BACKEND / "alembic"))
    command.upgrade(config, "head")


async def _vider_toutes_les_tables(moteur: AsyncEngine) -> None:
    from app.db.base import Base

    noms_tables = [table.name for table in Base.metadata.sorted_tables]
    async with moteur.begin() as connexion:
        await connexion.execute(
            text(f"TRUNCATE TABLE {', '.join(noms_tables)} RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture
async def session(_url_asyncpg: str) -> AsyncGenerator[AsyncSession, None]:
    moteur = create_async_engine(_url_asyncpg)
    fabrique = async_sessionmaker(moteur, expire_on_commit=False)

    async with fabrique() as s:
        yield s

    await _vider_toutes_les_tables(moteur)
    await moteur.dispose()


@pytest_asyncio.fixture
async def client(_url_asyncpg: str) -> AsyncGenerator[AsyncClient, None]:
    from app.db.session import get_session
    from app.main import app

    moteur = create_async_engine(_url_asyncpg)
    fabrique = async_sessionmaker(moteur, expire_on_commit=False)

    async def _get_session_test() -> AsyncGenerator[AsyncSession, None]:
        async with fabrique() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session_test

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await _vider_toutes_les_tables(moteur)
    await moteur.dispose()
