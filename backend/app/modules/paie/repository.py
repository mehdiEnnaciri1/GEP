"""Requêtes SQLAlchemy du module paie. Aucune règle métier ici — génération,
verrouillage et ajustements sont orchestrés par le service."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eleves.models import Eleve, InscriptionMatiere, StatutEleve
from app.modules.paie.models import LignePaie, PaieMensuelle
from app.modules.paiements.models import Echeance, StatutEcheance
from app.shared.periode import dernier_jour, premier_jour


class PaieMensuelleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, paie_id: int) -> PaieMensuelle | None:
        return await self._session.get(PaieMensuelle, paie_id)

    async def get_par_cle(self, professeur_id: int, periode: str) -> PaieMensuelle | None:
        resultat = await self._session.execute(
            select(PaieMensuelle).where(
                PaieMensuelle.professeur_id == professeur_id, PaieMensuelle.periode == periode
            )
        )
        return resultat.scalar_one_or_none()

    async def lister_par_periode(self, periode: str) -> list[PaieMensuelle]:
        resultat = await self._session.execute(
            select(PaieMensuelle).where(PaieMensuelle.periode == periode)
        )
        return list(resultat.scalars().all())

    async def lister_par_professeur(self, professeur_id: int) -> list[PaieMensuelle]:
        resultat = await self._session.execute(
            select(PaieMensuelle)
            .where(PaieMensuelle.professeur_id == professeur_id)
            .order_by(PaieMensuelle.periode.desc())
        )
        return list(resultat.scalars().all())

    async def creer(self, paie: PaieMensuelle) -> PaieMensuelle:
        self._session.add(paie)
        await self._session.flush()
        return paie


class LignePaieRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister_par_paie(self, paie_id: int) -> list[LignePaie]:
        resultat = await self._session.execute(
            select(LignePaie).where(LignePaie.paie_id == paie_id)
        )
        return list(resultat.scalars().all())

    async def creer(self, ligne: LignePaie) -> LignePaie:
        self._session.add(ligne)
        await self._session.flush()
        return ligne

    async def supprimer_lignes_generees(self, paie_id: int) -> None:
        """Les lignes d'ajustement (`est_ajustement`) survivent à une
        régénération — seules les lignes calculées sont recréées."""
        await self._session.execute(
            delete(LignePaie).where(
                LignePaie.paie_id == paie_id, LignePaie.est_ajustement.is_(False)
            )
        )


class CompteurElevesRepository:
    """Compte les élèves pour la formule de paie (§8.3 de
    docs/02-modele-donnees.md) — distinct du compteur d'affectation de
    l'étape 5 (celui-ci est sensible à la période et à `base_calcul_paie`)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compter(
        self,
        *,
        niveau_code: str,
        matiere_id: int,
        annee_scolaire_id: int,
        periode: str,
        base_calcul: str,
    ) -> int:
        borne_debut = premier_jour(periode)
        borne_fin = dernier_jour(periode)

        requete = (
            select(Eleve.id)
            .join(InscriptionMatiere, InscriptionMatiere.eleve_id == Eleve.id)
            .where(
                Eleve.statut == StatutEleve.ACTIF,
                Eleve.niveau_code == niveau_code,
                Eleve.annee_scolaire_id == annee_scolaire_id,
                InscriptionMatiere.matiere_id == matiere_id,
                InscriptionMatiere.date_debut <= borne_fin,
                (InscriptionMatiere.date_fin.is_(None))
                | (InscriptionMatiere.date_fin >= borne_debut),
            )
        )

        if base_calcul == "payants":
            requete = requete.join(
                Echeance,
                (Echeance.eleve_id == Eleve.id) & (Echeance.periode == periode),
            ).where(Echeance.statut.in_([StatutEcheance.PAYE, StatutEcheance.PARTIEL]))

        resultat = await self._session.execute(requete)
        return len(resultat.all())
