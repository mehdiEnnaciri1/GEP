"""Requêtes SQLAlchemy du module paiements. Aucune règle métier ici — le
recalcul du statut d'échéance et l'idempotence sont orchestrés par le service."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.paiements.models import Echeance, LigneEcheance, Paiement, StatutEcheance


class EcheanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_eleve_et_periode(self, eleve_id: int, periode: str) -> Echeance | None:
        resultat = await self._session.execute(
            select(Echeance).where(Echeance.eleve_id == eleve_id, Echeance.periode == periode)
        )
        return resultat.scalar_one_or_none()

    async def get_by_id(self, echeance_id: int) -> Echeance | None:
        return await self._session.get(Echeance, echeance_id)

    async def creer(self, echeance: Echeance) -> Echeance:
        self._session.add(echeance)
        await self._session.flush()
        return echeance

    async def creer_ligne(self, ligne: LigneEcheance) -> LigneEcheance:
        self._session.add(ligne)
        await self._session.flush()
        return ligne

    async def lister_impayes(self, periode: str) -> list[Echeance]:
        resultat = await self._session.execute(
            select(Echeance).where(
                Echeance.periode == periode, Echeance.statut != StatutEcheance.PAYE
            )
        )
        return list(resultat.scalars().all())


class PaiementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, paiement_id: int) -> Paiement | None:
        return await self._session.get(Paiement, paiement_id)

    async def get_by_cle_idempotence(self, cle: uuid.UUID) -> Paiement | None:
        resultat = await self._session.execute(
            select(Paiement).where(Paiement.cle_idempotence == cle)
        )
        return resultat.scalar_one_or_none()

    async def creer(self, paiement: Paiement) -> Paiement:
        self._session.add(paiement)
        await self._session.flush()
        return paiement

    async def compter_annee(self, annee: int) -> int:
        resultat = await self._session.execute(
            select(func.count()).where(Paiement.numero_recu.like(f"R-{annee}-%"))
        )
        return resultat.scalar_one()

    async def lister_par_eleve(self, eleve_id: int) -> list[Paiement]:
        resultat = await self._session.execute(
            select(Paiement)
            .where(Paiement.eleve_id == eleve_id)
            .order_by(Paiement.date_paiement.desc(), Paiement.id.desc())
        )
        return list(resultat.scalars().all())
