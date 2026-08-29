"""Requêtes SQLAlchemy du module dashboard. Aucune règle métier ici — la
composition des indicateurs (dont le bénéfice net) est orchestrée par le
service. Toutes les agrégations sont faites en base (`SUM`/`COUNT`/`GROUP BY`),
jamais en itérant des lignes côté Python."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.charges.models import CategorieCharge, Charge
from app.modules.eleves.models import Eleve, InscriptionMatiere, StatutEleve
from app.modules.paie.models import PaieMensuelle, StatutPaie
from app.modules.paiements.models import Echeance, Paiement, StatutEcheance, TypePaiement
from app.modules.professeurs.models import Professeur
from app.shared.periode import dernier_jour, premier_jour


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compter_eleves_actifs(self, annee_scolaire_id: int) -> int:
        resultat = await self._session.execute(
            select(func.count())
            .select_from(Eleve)
            .where(Eleve.statut == StatutEleve.ACTIF, Eleve.annee_scolaire_id == annee_scolaire_id)
        )
        return int(resultat.scalar_one())

    async def compter_eleves_par_niveau(self, annee_scolaire_id: int) -> list[tuple[str, int]]:
        resultat = await self._session.execute(
            select(Eleve.niveau_code, func.count())
            .where(Eleve.statut == StatutEleve.ACTIF, Eleve.annee_scolaire_id == annee_scolaire_id)
            .group_by(Eleve.niveau_code)
        )
        return [(niveau, int(compte)) for niveau, compte in resultat.all()]

    async def compter_professeurs_actifs(self) -> int:
        resultat = await self._session.execute(
            select(func.count()).select_from(Professeur).where(Professeur.actif.is_(True))
        )
        return int(resultat.scalar_one())

    async def total_encaissements_mensualites(self, periode: str) -> int:
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(Paiement.montant_cents), 0)).where(
                Paiement.type == TypePaiement.MENSUALITE,
                Paiement.periode == periode,
                Paiement.annule_le.is_(None),
            )
        )
        return int(resultat.scalar_one())

    async def total_encaissements_inscriptions(self, periode: str) -> int:
        # §8.4 : les frais d'inscription n'ont pas de colonne `periode` (un
        # seul par élève, jamais lié à un mois précis) — on se base sur le
        # mois calendaire de `date_paiement`, comme le modèle de données le
        # précise explicitement pour cet indicateur.
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(Paiement.montant_cents), 0)).where(
                Paiement.type == TypePaiement.INSCRIPTION,
                Paiement.date_paiement >= premier_jour(periode),
                Paiement.date_paiement <= dernier_jour(periode),
                Paiement.annule_le.is_(None),
            )
        )
        return int(resultat.scalar_one())

    async def total_impayes(self, periode: str) -> int:
        resultat = await self._session.execute(
            select(
                func.coalesce(func.sum(Echeance.montant_du_cents - Echeance.montant_paye_cents), 0)
            ).where(Echeance.periode == periode, Echeance.statut != StatutEcheance.PAYE)
        )
        return int(resultat.scalar_one())

    async def total_charges(self, periode: str) -> int:
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(Charge.montant_cents), 0)).where(
                Charge.periode == periode, Charge.annule_le.is_(None)
            )
        )
        return int(resultat.scalar_one())

    async def compter_eleves_actifs_periode(self, annee_scolaire_id: int, periode: str) -> int:
        """Élèves de `annee_scolaire_id` comptant pour `periode` (graphe
        d'évolution des effectifs) : non ARCHIVE, avec au moins une inscription
        à une matière active durant le mois. Un SUSPENDU compte quand même
        s'il avait une inscription active (§8 de docs/02-modele-donnees.md) —
        seul ARCHIVE exclut."""
        borne_debut = premier_jour(periode)
        borne_fin = dernier_jour(periode)
        resultat = await self._session.execute(
            select(func.count(func.distinct(Eleve.id)))
            .select_from(Eleve)
            .join(InscriptionMatiere, InscriptionMatiere.eleve_id == Eleve.id)
            .where(
                Eleve.annee_scolaire_id == annee_scolaire_id,
                Eleve.statut != StatutEleve.ARCHIVE,
                InscriptionMatiere.date_debut <= borne_fin,
                (InscriptionMatiere.date_fin.is_(None))
                | (InscriptionMatiere.date_fin >= borne_debut),
            )
        )
        return int(resultat.scalar_one())

    async def total_loyer(self, periode: str) -> int:
        """Sous-ensemble de `total_charges` : uniquement la catégorie « Loyer »
        (libellé exact, seed dans `app/db/seeds.py`) — sert au calcul ADMIN de
        `montant_frais_inscription_cumules_cents` (voir
        docs/adr/2026-08-16-marge-hors-loyer.md)."""
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(Charge.montant_cents), 0))
            .select_from(Charge)
            .join(CategorieCharge, CategorieCharge.id == Charge.categorie_id)
            .where(
                Charge.periode == periode,
                Charge.annule_le.is_(None),
                CategorieCharge.libelle == "Loyer",
            )
        )
        return int(resultat.scalar_one())

    async def total_paie_hors_brouillon(self, periode: str) -> int:
        resultat = await self._session.execute(
            select(func.coalesce(func.sum(PaieMensuelle.total_cents), 0)).where(
                PaieMensuelle.periode == periode, PaieMensuelle.statut != StatutPaie.BROUILLON
            )
        )
        return int(resultat.scalar_one())
