"""Schémas Pydantic — sortie du module dashboard."""

from __future__ import annotations

from pydantic import BaseModel


class IndicateurNiveauEleves(BaseModel):
    niveau_code: str
    nombre: int


class IndicateursRestreints(BaseModel):
    """Vue caissier (§6.6) : ni charges, ni paie, ni bénéfice net."""

    periode: str
    nombre_eleves_total: int
    nombre_eleves_par_niveau: list[IndicateurNiveauEleves]
    montant_total_encaisse_cents: int
    montant_frais_inscription_cumules_cents: int
    montant_impayes_cents: int
    nombre_professeurs: int


class IndicateursComplets(IndicateursRestreints):
    """Vue admin : ajoute charges, paie et bénéfice net (décision D2)."""

    total_charges_cents: int
    total_paie_cents: int
    benefice_net_cents: int
    # Indicateur de couverture, distinct du bénéfice net : le loyer reste
    # compté dans total_charges_cents et benefice_net_cents ci-dessus, celui-ci
    # est un indicateur supplémentaire, pas un remplacement — voir
    # docs/adr/2026-08-16-marge-hors-loyer.md.
    marge_hors_loyer_cents: int


class PointEffectif(BaseModel):
    mois: int
    nb: int


class EvolutionAnnee(BaseModel):
    libelle: str
    points: list[PointEffectif]


class EvolutionEffectifsReponse(BaseModel):
    """Graphe fixe du dashboard — une ligne par année scolaire, indépendant du
    filtre de période mensuel. `points` va toujours de septembre à août,
    12 éléments, `mois` porte le numéro de mois calendaire (1-12)."""

    annees: list[EvolutionAnnee]
