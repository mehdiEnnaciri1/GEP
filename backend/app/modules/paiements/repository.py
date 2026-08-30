"""Requêtes SQLAlchemy du module paiements. Aucune règle métier ici — le
recalcul du statut d'échéance et l'idempotence sont orchestrés par le service."""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.paiements.models import (
    Echeance,
    LigneEcheance,
    Paiement,
    StatutEcheance,
    TypePaiement,
)
from app.shared.periode import dernier_jour, premier_jour


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

    async def lister_impayes(
        self, periode: str, statut: StatutEcheance | None = None
    ) -> list[Echeance]:
        """Sans `statut` : toutes les échéances de la période (payées ou
        non) — le nom garde « impayes » pour ne pas casser l'URL existante,
        mais la liste couvre désormais Payé/Impayé, filtrable par statut."""
        conditions = [Echeance.periode == periode]
        if statut is not None:
            conditions.append(Echeance.statut == statut)
        resultat = await self._session.execute(select(Echeance).where(*conditions))
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

    async def prochain_numero_recu(self) -> int:
        """Même principe que `EleveRepository.prochain_numero_matricule` :
        `nextval()` atomique, pas un comptage sujet à une course entre deux
        encaissements simultanés."""
        resultat = await self._session.execute(text("SELECT nextval('seq_numero_recu_paiement')"))
        return int(resultat.scalar_one())

    async def lister_par_eleve(self, eleve_id: int) -> list[Paiement]:
        resultat = await self._session.execute(
            select(Paiement)
            .where(Paiement.eleve_id == eleve_id)
            .order_by(Paiement.date_paiement.desc(), Paiement.id.desc())
        )
        return list(resultat.scalars().all())

    async def lister_par_periode(self, periode: str) -> list[Paiement]:
        """Mensualités de `periode`, et frais d'inscription payés dans le
        mois calendaire de `periode` — même définition que le dashboard
        (§8.4) pour rester cohérent avec `montant_total_encaisse`."""
        borne_debut = premier_jour(periode)
        borne_fin = dernier_jour(periode)
        resultat = await self._session.execute(
            select(Paiement)
            .where(
                (Paiement.type == TypePaiement.MENSUALITE) & (Paiement.periode == periode)
                | (
                    (Paiement.type == TypePaiement.INSCRIPTION)
                    & (Paiement.date_paiement >= borne_debut)
                    & (Paiement.date_paiement <= borne_fin)
                )
            )
            .order_by(Paiement.date_paiement.desc(), Paiement.id.desc())
        )
        return list(resultat.scalars().all())
