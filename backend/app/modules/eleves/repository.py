"""Requêtes SQLAlchemy du module eleves. Aucune règle métier ici — la
génération du matricule et la copie du tarif sont orchestrées par le service."""

from __future__ import annotations

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eleves.models import Eleve, FraisInscription, InscriptionMatiere, StatutEleve


class EleveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, eleve_id: int) -> Eleve | None:
        return await self._session.get(Eleve, eleve_id)

    async def creer(self, eleve: Eleve) -> Eleve:
        self._session.add(eleve)
        await self._session.flush()
        return eleve

    async def prochain_numero_matricule(self) -> int:
        """`nextval()` est atomique côté Postgres : deux créations d'élève
        concurrentes obtiennent toujours deux valeurs distinctes — un
        `SELECT count(*) + 1` ne le garantirait pas (course possible entre
        les deux comptages avant que l'une des insertions ne commite)."""
        resultat = await self._session.execute(text("SELECT nextval('seq_matricule_eleve')"))
        return int(resultat.scalar_one())

    async def lister_actifs_par_annee(self, annee_scolaire_id: int) -> list[Eleve]:
        resultat = await self._session.execute(
            select(Eleve).where(
                Eleve.statut == StatutEleve.ACTIF, Eleve.annee_scolaire_id == annee_scolaire_id
            )
        )
        return list(resultat.scalars().all())

    async def lister(
        self,
        *,
        recherche: str | None,
        niveau_code: str | None,
        statut: StatutEleve | None,
        page: int,
        taille: int,
    ) -> tuple[list[Eleve], int]:
        requete = select(Eleve)

        if recherche:
            motif = f"%{recherche}%"
            requete = requete.where(or_(Eleve.nom.ilike(motif), Eleve.prenom.ilike(motif)))
        if niveau_code:
            requete = requete.where(Eleve.niveau_code == niveau_code)
        if statut:
            requete = requete.where(Eleve.statut == statut)

        total = (
            await self._session.execute(select(func.count()).select_from(requete.subquery()))
        ).scalar_one()

        requete = (
            requete.order_by(Eleve.nom, Eleve.prenom).offset((page - 1) * taille).limit(taille)
        )
        elements = list((await self._session.execute(requete)).scalars().all())

        return elements, total


class InscriptionMatiereRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def creer(self, inscription: InscriptionMatiere) -> InscriptionMatiere:
        self._session.add(inscription)
        await self._session.flush()
        return inscription

    async def lister_par_eleve(self, eleve_id: int) -> list[InscriptionMatiere]:
        resultat = await self._session.execute(
            select(InscriptionMatiere).where(InscriptionMatiere.eleve_id == eleve_id)
        )
        return list(resultat.scalars().all())


class FraisInscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def creer(self, frais: FraisInscription) -> FraisInscription:
        self._session.add(frais)
        await self._session.flush()
        return frais

    async def get_by_eleve(self, eleve_id: int) -> FraisInscription | None:
        resultat = await self._session.execute(
            select(FraisInscription).where(FraisInscription.eleve_id == eleve_id)
        )
        return resultat.scalar_one_or_none()
