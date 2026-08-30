"""Service du module dashboard — lecture seule, aucun commit (voir
§Couches de CLAUDE.md : seules les écritures ont besoin d'une transaction).

Bénéfice net (décision D2, docs/03-decisions-ouvertes.md) : les encaissements
MENSUALITE et INSCRIPTION sont disjoints par construction (`paiement.type`),
la somme est donc exacte — pas de double comptage des frais d'inscription.
`total_paie_cents` exclut les paies BROUILLON : une paie non validée n'est
pas un engagement du centre, elle ne doit pas dégrader le bénéfice affiché.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationMetier
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    EvolutionAnnee,
    EvolutionEffectifsReponse,
    IndicateurNiveauEleves,
    IndicateursComplets,
    IndicateursRestreints,
    PointEffectif,
)
from app.modules.referentiel.models import AnneeScolaire
from app.modules.referentiel.repository import AnneeScolaireRepository

# Une année scolaire commence toujours en août (convention du graphe
# d'évolution des effectifs, indépendante de date_debut/date_fin réels de
# l'année, qui peuvent varier légèrement) — 8,9,10,11,12 puis 1..7.
_MOIS_ANNEE_SCOLAIRE = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._dashboard = DashboardRepository(session)
        self._annees = AnneeScolaireRepository(session)

    async def _annee_active(self) -> AnneeScolaire:
        annee = next((a for a in await self._annees.lister() if a.est_active), None)
        if annee is None:
            raise ValidationMetier(
                "Aucune année scolaire active — le dashboard n'a rien à afficher."
            )
        return annee

    async def annees_disponibles(self) -> list[AnneeScolaire]:
        return await self._annees.lister()

    async def indicateurs_restreints(self, periode: str) -> IndicateursRestreints:
        annee = await self._annee_active()

        nombre_eleves_total = await self._dashboard.compter_eleves_actifs(annee.id)
        par_niveau = await self._dashboard.compter_eleves_par_niveau(annee.id)
        nombre_professeurs = await self._dashboard.compter_professeurs_actifs()
        encaissements_mensualites = await self._dashboard.total_encaissements_mensualites(periode)
        encaissements_inscriptions = await self._dashboard.total_encaissements_inscriptions(periode)
        montant_impayes = await self._dashboard.total_impayes(periode)

        return IndicateursRestreints(
            periode=periode,
            nombre_eleves_total=nombre_eleves_total,
            nombre_eleves_par_niveau=[
                IndicateurNiveauEleves(niveau_code=niveau, nombre=nombre)
                for niveau, nombre in par_niveau
            ],
            # « Encaissé ce mois » = mensualités seules, les frais
            # d'inscription ont leur propre carte (montant_frais_inscription_
            # cumules_cents) — ne pas les compter deux fois à l'écran. Le
            # bénéfice net (ci-dessous) continue lui à sommer les deux.
            montant_total_encaisse_cents=encaissements_mensualites,
            montant_frais_inscription_cumules_cents=encaissements_inscriptions,
            montant_impayes_cents=montant_impayes,
            nombre_professeurs=nombre_professeurs,
        )

    async def indicateurs_complets(self, periode: str) -> IndicateursComplets:
        restreints = await self.indicateurs_restreints(periode)
        total_charges = await self._dashboard.total_charges(periode)
        total_paie = await self._dashboard.total_paie_hors_brouillon(periode)
        # Le bénéfice net somme mensualités ET frais d'inscription (décision
        # D2), contrairement à « Encaissé ce mois » qui n'affiche que les
        # mensualités — les deux valeurs sources restent disponibles ici,
        # séparément, avant que frais_inscription_nets ne les remplace plus bas.
        encaissements_totaux = (
            restreints.montant_total_encaisse_cents
            + restreints.montant_frais_inscription_cumules_cents
        )
        benefice_net = encaissements_totaux - total_charges - total_paie

        # Frais d'inscription cumulés, vue ADMIN uniquement : frais moins les
        # charges HORS loyer — pas la somme brute que voit IndicateursRestreints
        # (voir docstring du schéma). Le loyer ne réduit pas ce chiffre.
        total_loyer = await self._dashboard.total_loyer(periode)
        frais_inscription_nets = restreints.montant_frais_inscription_cumules_cents - (
            total_charges - total_loyer
        )

        donnees = restreints.model_dump()
        donnees["montant_frais_inscription_cumules_cents"] = frais_inscription_nets

        return IndicateursComplets(
            **donnees,
            total_charges_cents=total_charges,
            total_paie_cents=total_paie,
            benefice_net_cents=benefice_net,
        )

    async def evolution_effectifs(self) -> EvolutionEffectifsReponse:
        annees_scolaires = []
        for annee in await self._annees.lister():
            annee_debut = int(annee.libelle.split("-")[0])
            points = []
            for mois in _MOIS_ANNEE_SCOLAIRE:
                annee_civile = annee_debut if mois >= 8 else annee_debut + 1
                periode = f"{annee_civile:04d}-{mois:02d}"
                nb = await self._dashboard.compter_eleves_actifs_periode(annee.id, periode)
                points.append(PointEffectif(mois=mois, nb=nb))
            annees_scolaires.append(EvolutionAnnee(libelle=annee.libelle, points=points))

        return EvolutionEffectifsReponse(annees=annees_scolaires)
