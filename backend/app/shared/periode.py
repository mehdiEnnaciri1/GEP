"""Manipulation des périodes mensuelles au format YYYY-MM.

Une période est une chaîne `CHAR(7)`, ex. "2025-10" — voir §6.7 de
`docs/01-architecture.md`. Ce module est la référence unique pour la valider,
la parcourir et la situer dans le calendrier. Le format est celui de la
contrainte `CHECK` posée sur les tables `echeance` et `charge`.
"""

from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSEAU_HORAIRE_CENTRE = ZoneInfo("Africa/Casablanca")

_FORMAT_PERIODE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def valider_periode(periode: str) -> None:
    """Lève `ValueError` si `periode` n'est pas au format YYYY-MM."""
    if not _FORMAT_PERIODE.match(periode):
        raise ValueError(f"Période invalide : {periode!r}, attendu le format YYYY-MM.")


def periode_courante() -> str:
    """Période du jour, dans le fuseau horaire du centre (Africa/Casablanca).

    Ne jamais remplacer par un décalage fixe codé en dur : le Maroc applique
    un décalage saisonnier lié au Ramadan (voir §6.7).
    """
    maintenant = datetime.now(FUSEAU_HORAIRE_CENTRE)
    return f"{maintenant.year:04d}-{maintenant.month:02d}"


def depuis_date(jour: date) -> str:
    """Période YYYY-MM à laquelle appartient `jour`."""
    return f"{jour.year:04d}-{jour.month:02d}"


def premier_jour(periode: str) -> date:
    """Premier jour calendaire de la période."""
    annee, mois = _decomposer(periode)
    return date(annee, mois, 1)


def dernier_jour(periode: str) -> date:
    """Dernier jour calendaire de la période (28, 29, 30 ou 31 selon le mois)."""
    annee, mois = _decomposer(periode)
    _, nb_jours = monthrange(annee, mois)
    return date(annee, mois, nb_jours)


def periode_suivante(periode: str) -> str:
    """Période immédiatement après `periode`."""
    annee, mois = _decomposer(periode)
    if mois == 12:
        return f"{annee + 1:04d}-01"
    return f"{annee:04d}-{mois + 1:02d}"


def periode_precedente(periode: str) -> str:
    """Période immédiatement avant `periode`."""
    annee, mois = _decomposer(periode)
    if mois == 1:
        return f"{annee - 1:04d}-12"
    return f"{annee:04d}-{mois - 1:02d}"


def _decomposer(periode: str) -> tuple[int, int]:
    valider_periode(periode)
    annee_str, mois_str = periode.split("-")
    return int(annee_str), int(mois_str)
