"""Requêtes SQLAlchemy du module professeurs. Aucune règle métier ici — le
refus d'une affectation en conflit est orchestré par le service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eleves.models import Eleve, InscriptionMatiere, StatutEleve
from app.modules.professeurs.models import Affectation, Professeur


class ProfesseurRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, professeur_id: int) -> Professeur | None:
        return await self._session.get(Professeur, professeur_id)

    async def lister(self) -> list[Professeur]:
        resultat = await self._session.execute(
            select(Professeur).order_by(Professeur.nom, Professeur.prenom)
        )
        return list(resultat.scalars().all())

    async def creer(self, professeur: Professeur) -> Professeur:
        self._session.add(professeur)
        await self._session.flush()
        return professeur


class AffectationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, affectation_id: int) -> Affectation | None:
        return await self._session.get(Affectation, affectation_id)

    async def get_par_cle(
        self, annee_scolaire_id: int, matiere_id: int, niveau_code: str
    ) -> Affectation | None:
        resultat = await self._session.execute(
            select(Affectation).where(
                Affectation.annee_scolaire_id == annee_scolaire_id,
                Affectation.matiere_id == matiere_id,
                Affectation.niveau_code == niveau_code,
            )
        )
        return resultat.scalar_one_or_none()

    async def lister(
        self, *, annee_scolaire_id: int | None = None, professeur_id: int | None = None
    ) -> list[Affectation]:
        requete = select(Affectation)
        if annee_scolaire_id is not None:
            requete = requete.where(Affectation.annee_scolaire_id == annee_scolaire_id)
        if professeur_id is not None:
            requete = requete.where(Affectation.professeur_id == professeur_id)
        resultat = await self._session.execute(requete)
        return list(resultat.scalars().all())

    async def creer(self, affectation: Affectation) -> Affectation:
        self._session.add(affectation)
        await self._session.flush()
        return affectation

    async def supprimer(self, affectation: Affectation) -> None:
        await self._session.delete(affectation)
        await self._session.flush()

    async def compter_eleves(
        self, *, niveau_code: str, matiere_id: int, annee_scolaire_id: int
    ) -> int:
        """§8.3 de docs/02-modele-donnees.md : élèves ACTIF du niveau et de
        l'année, ayant une inscription EN COURS (`date_fin IS NULL`) à la
        matière — même filtre que celui utilisé par le calcul de paie."""

        resultat = await self._session.execute(
            select(Eleve.id)
            .join(InscriptionMatiere, InscriptionMatiere.eleve_id == Eleve.id)
            .where(
                Eleve.statut == StatutEleve.ACTIF,
                Eleve.niveau_code == niveau_code,
                Eleve.annee_scolaire_id == annee_scolaire_id,
                InscriptionMatiere.matiere_id == matiere_id,
                InscriptionMatiere.date_fin.is_(None),
            )
        )
        return len(resultat.all())
