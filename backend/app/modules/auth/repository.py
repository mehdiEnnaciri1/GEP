"""Requêtes SQLAlchemy sur `utilisateur`. Aucune règle métier ici."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Utilisateur


class UtilisateurRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Utilisateur | None:
        resultat = await self._session.execute(
            select(Utilisateur).where(Utilisateur.email == email)
        )
        return resultat.scalar_one_or_none()

    async def get_by_id(self, utilisateur_id: int) -> Utilisateur | None:
        return await self._session.get(Utilisateur, utilisateur_id)

    async def lister(self) -> list[Utilisateur]:
        resultat = await self._session.execute(select(Utilisateur).order_by(Utilisateur.nom))
        return list(resultat.scalars().all())

    async def marquer_derniere_connexion(self, utilisateur: Utilisateur) -> None:
        utilisateur.derniere_connexion = datetime.now(UTC)
        self._session.add(utilisateur)

    async def creer(self, utilisateur: Utilisateur) -> Utilisateur:
        self._session.add(utilisateur)
        await self._session.flush()
        return utilisateur
