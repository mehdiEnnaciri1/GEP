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
    IndicateurNiveauEleves,
    IndicateursComplets,
    IndicateursRestreints,
)
from app.modules.referentiel.models import AnneeScolaire
from app.modules.referentiel.repository import AnneeScolaireRepository


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
            montant_total_encaisse_cents=encaissements_mensualites + encaissements_inscriptions,
            montant_frais_inscription_cumules_cents=encaissements_inscriptions,
            montant_impayes_cents=montant_impayes,
            nombre_professeurs=nombre_professeurs,
        )

    async def indicateurs_complets(self, periode: str) -> IndicateursComplets:
        restreints = await self.indicateurs_restreints(periode)
        total_charges = await self._dashboard.total_charges(periode)
        total_paie = await self._dashboard.total_paie_hors_brouillon(periode)
        benefice_net = restreints.montant_total_encaisse_cents - total_charges - total_paie

        return IndicateursComplets(
            **restreints.model_dump(),
            total_charges_cents=total_charges,
            total_paie_cents=total_paie,
            benefice_net_cents=benefice_net,
        )
