"""Services du module professeurs — frontière transactionnelle. Chaque
méthode commite elle-même son unité de travail (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable
from app.modules.professeurs.models import Affectation, Professeur
from app.modules.professeurs.repository import AffectationRepository, ProfesseurRepository
from app.modules.professeurs.schemas import (
    AffectationCreation,
    ProfesseurCreation,
    ProfesseurMiseAJour,
)
from app.modules.referentiel.repository import (
    AnneeScolaireRepository,
    MatiereRepository,
    NiveauRepository,
)


class ProfesseurService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._professeurs = ProfesseurRepository(session)
        self._affectations = AffectationRepository(session)

    async def lister(self) -> list[Professeur]:
        return await self._professeurs.lister()

    async def creer(self, donnees: ProfesseurCreation) -> Professeur:
        professeur = await self._professeurs.creer(
            Professeur(nom=donnees.nom, prenom=donnees.prenom, telephone=donnees.telephone)
        )
        await self._session.commit()
        return professeur

    async def mettre_a_jour(self, professeur_id: int, donnees: ProfesseurMiseAJour) -> Professeur:
        professeur = await self._professeurs.get_by_id(professeur_id)
        if professeur is None:
            raise RessourceIntrouvable(f"Professeur {professeur_id} introuvable.")

        for champ, valeur in donnees.model_dump(exclude_unset=True).items():
            setattr(professeur, champ, valeur)

        await self._session.commit()
        return professeur

    async def obtenir_detail(
        self, professeur_id: int
    ) -> tuple[Professeur, list[tuple[Affectation, int]]]:
        professeur = await self._professeurs.get_by_id(professeur_id)
        if professeur is None:
            raise RessourceIntrouvable(f"Professeur {professeur_id} introuvable.")

        affectations = await self._affectations.lister(professeur_id=professeur_id)
        avec_compteur = [
            (
                affectation,
                await self._affectations.compter_eleves(
                    niveau_code=affectation.niveau_code,
                    matiere_id=affectation.matiere_id,
                    annee_scolaire_id=affectation.annee_scolaire_id,
                ),
            )
            for affectation in affectations
        ]
        return professeur, avec_compteur


class AffectationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._professeurs = ProfesseurRepository(session)
        self._affectations = AffectationRepository(session)
        self._annees = AnneeScolaireRepository(session)
        self._niveaux = NiveauRepository(session)
        self._matieres = MatiereRepository(session)

    async def creer(self, donnees: AffectationCreation) -> Affectation:
        if await self._professeurs.get_by_id(donnees.professeur_id) is None:
            raise RessourceIntrouvable(f"Professeur {donnees.professeur_id} introuvable.")
        if await self._annees.get_by_id(donnees.annee_scolaire_id) is None:
            raise RessourceIntrouvable(f"Année scolaire {donnees.annee_scolaire_id} introuvable.")
        if not await self._niveaux.existe(donnees.niveau_code):
            raise RessourceIntrouvable(f"Niveau {donnees.niveau_code} introuvable.")
        if await self._matieres.get_by_id(donnees.matiere_id) is None:
            raise RessourceIntrouvable(f"Matière {donnees.matiere_id} introuvable.")

        # Décision D3 (voir le commentaire du modèle `Affectation`) : un seul
        # professeur par couple (année, matière, niveau). Le message nomme
        # explicitement le professeur qui occupe déjà le couple, plutôt que
        # de laisser remonter la seule violation de contrainte Postgres.
        existante = await self._affectations.get_par_cle(
            donnees.annee_scolaire_id, donnees.matiere_id, donnees.niveau_code
        )
        if existante is not None:
            occupant = await self._professeurs.get_by_id(existante.professeur_id)
            assert occupant is not None
            raise ConflitMetier(
                f"Ce couple (matière, niveau) est déjà affecté à "
                f"{occupant.prenom} {occupant.nom} pour cette année scolaire."
            )

        affectation = await self._affectations.creer(
            Affectation(
                professeur_id=donnees.professeur_id,
                matiere_id=donnees.matiere_id,
                niveau_code=donnees.niveau_code,
                annee_scolaire_id=donnees.annee_scolaire_id,
                date_debut=donnees.date_debut,
                date_fin=donnees.date_fin,
            )
        )
        await self._session.commit()
        return affectation

    async def lister(
        self, *, annee_scolaire_id: int | None, professeur_id: int | None
    ) -> list[tuple[Affectation, int]]:
        affectations = await self._affectations.lister(
            annee_scolaire_id=annee_scolaire_id, professeur_id=professeur_id
        )
        return [
            (
                affectation,
                await self._affectations.compter_eleves(
                    niveau_code=affectation.niveau_code,
                    matiere_id=affectation.matiere_id,
                    annee_scolaire_id=affectation.annee_scolaire_id,
                ),
            )
            for affectation in affectations
        ]

    async def supprimer(self, affectation_id: int) -> None:
        affectation = await self._affectations.get_by_id(affectation_id)
        if affectation is None:
            raise RessourceIntrouvable(f"Affectation {affectation_id} introuvable.")

        await self._affectations.supprimer(affectation)
        await self._session.commit()
