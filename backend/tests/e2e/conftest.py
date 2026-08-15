"""Fixtures partagées aux tests e2e (endpoints via httpx, sur une vraie base).

Deux modes, sélectionnés par la variable d'environnement `GEP_TEST_DATABASE_URL` :

- **définie** : on s'y connecte directement, aucun conteneur démarré. C'est le
  mode à utiliser en local tant que Docker Desktop est instable sur ce poste —
  voir README.md pour créer la base de test et l'URL à exporter.
- **absente** : repli sur testcontainers (un vrai Postgres jetable), le bon
  défaut en CI où Docker est fiable et où il n'y a pas de base de dev à
  préserver.

Dans les deux cas, les migrations sont jouées une fois par session de tests,
puis chaque test reçoit une session et un client HTTP propres ; les tables
sont vidées après chaque test pour l'isolation (les endpoints commitent
eux-mêmes, un simple rollback ne suffirait pas).

Volontairement dans `tests/e2e/`, pas à la racine de `tests/` : un conftest
racine avec ces fixtures en `autouse` ferait démarrer un conteneur Postgres
(ou exiger `GEP_TEST_DATABASE_URL`) même pour les tests unitaires purs de
`tests/unit/`, qui n'en ont pas besoin.
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

# app.db.session (importé dès que app.main l'est, via les routers) construit
# un moteur à partir de obtenir_reglages() au moment de l'import — valeurs
# bidon, jamais utilisées pour une vraie connexion : le client de test et la
# fixture `session` ci-dessous construisent leur propre moteur à partir de
# l'URL réelle (GEP_TEST_DATABASE_URL ou conteneur).
os.environ.setdefault("SECRET_KEY", "cle-de-test-jamais-utilisee-en-production")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")


@pytest.fixture(scope="session")
def _conteneur_postgres() -> Iterator[PostgresContainer | None]:
    if os.environ.get("GEP_TEST_DATABASE_URL"):
        yield None
        return
    with PostgresContainer("postgres:16") as conteneur:
        yield conteneur


@pytest.fixture(scope="session")
def _url_asyncpg(_conteneur_postgres: PostgresContainer | None) -> str:
    url_env = os.environ.get("GEP_TEST_DATABASE_URL")
    if url_env:
        return url_env

    assert _conteneur_postgres is not None
    return (
        f"postgresql+asyncpg://{_conteneur_postgres.username}:{_conteneur_postgres.password}"
        f"@{_conteneur_postgres.get_container_host_ip()}"
        f":{_conteneur_postgres.get_exposed_port(5432)}/{_conteneur_postgres.dbname}"
    )


@pytest.fixture(scope="session", autouse=True)
def _migrer_base_test(_url_asyncpg: str) -> None:
    """Joue les migrations Alembic sur la base de test, une fois par session.
    L'URL est posée directement sur la config Alembic (alembic/env.py respecte
    une `sqlalchemy.url` déjà définie plutôt que de la recalculer depuis
    obtenir_reglages()) — pas de bricolage de POSTGRES_HOST/PORT/USER dans
    os.environ."""

    config = Config(str(_RACINE_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(_RACINE_BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", _url_asyncpg)
    command.upgrade(config, "head")


async def _vider_toutes_les_tables(moteur: AsyncEngine) -> None:
    from app.db.base import Base

    noms_tables = [table.name for table in Base.metadata.sorted_tables]
    async with moteur.begin() as connexion:
        await connexion.execute(
            text(f"TRUNCATE TABLE {', '.join(noms_tables)} RESTART IDENTITY CASCADE")
        )
        # Séquences autonomes (matricule, numéro de reçu) : TRUNCATE ...
        # RESTART IDENTITY ne les touche pas, elles n'appartiennent à aucune
        # colonne SERIAL/IDENTITY d'une table tronquée. Sans ce reset, un test
        # qui vérifie une valeur exacte (ex. "E-2025-0001") dépendrait de
        # l'ordre d'exécution des tests précédents.
        await connexion.execute(text("ALTER SEQUENCE seq_matricule_eleve RESTART WITH 1"))
        await connexion.execute(text("ALTER SEQUENCE seq_numero_recu_paiement RESTART WITH 1"))


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
