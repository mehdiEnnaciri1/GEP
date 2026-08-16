"""Requêtes SQLAlchemy du module charges. Aucune règle métier ici."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.charges.models import CategorieCharge, Charge


class CategorieChargeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister(self) -> list[CategorieCharge]:
        resultat = await self._session.execute(
            select(CategorieCharge).order_by(CategorieCharge.libelle)
        )
        return list(resultat.scalars().all())

    async def get_by_id(self, categorie_id: int) -> CategorieCharge | None:
        return await self._session.get(CategorieCharge, categorie_id)

    async def get_by_libelle(self, libelle: str) -> CategorieCharge | None:
        resultat = await self._session.execute(
            select(CategorieCharge).where(CategorieCharge.libelle == libelle)
        )
        return resultat.scalar_one_or_none()

    async def creer(self, categorie: CategorieCharge) -> CategorieCharge:
        self._session.add(categorie)
        await self._session.flush()
        return categorie


class ChargeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, charge_id: int) -> Charge | None:
        return await self._session.get(Charge, charge_id)

    async def creer(self, charge: Charge) -> Charge:
        self._session.add(charge)
        await self._session.flush()
        return charge

    async def lister(self, *, periode: str | None, categorie_id: int | None) -> list[Charge]:
        requete = select(Charge).where(Charge.annule_le.is_(None))
        if periode is not None:
            requete = requete.where(Charge.periode == periode)
        if categorie_id is not None:
            requete = requete.where(Charge.categorie_id == categorie_id)
        resultat = await self._session.execute(requete.order_by(Charge.date_charge.desc()))
        return list(resultat.scalars().all())

    async def total_periode(self, periode: str) -> int:
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(Charge.montant_cents), 0)).where(
                Charge.periode == periode, Charge.annule_le.is_(None)
            )
        )
        return int(resultat.scalar_one())

    async def total_par_categorie(self, periode: str) -> list[tuple[int, int]]:
        """Retourne [(categorie_id, total_cents), ...] pour la période."""
        resultat = await self._session.execute(
            select(Charge.categorie_id, func.sum(Charge.montant_cents))
            .where(Charge.periode == periode, Charge.annule_le.is_(None))
            .group_by(Charge.categorie_id)
        )
        return [(categorie_id, int(total)) for categorie_id, total in resultat.all()]
