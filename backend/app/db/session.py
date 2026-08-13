"""Moteur async et dépendance FastAPI d'obtention d'une session."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import obtenir_reglages

moteur = create_async_engine(obtenir_reglages().url_base_donnees, echo=False)

FabriqueSession = async_sessionmaker(moteur, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with FabriqueSession() as session:
        yield session
