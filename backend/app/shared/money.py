"""Conversions et formatage des montants monétaires.

Tout montant métier est un entier en centimes de dirham (BIGINT en base, int en
Python). Ce module est le seul endroit autorisé à diviser un montant par 100 :
toute conversion en dirhams, pour affichage ou export, passe par ici. Le
miroir côté frontend est `lib/money.ts`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS_PAR_DIRHAM = 100
DEVISE_PAR_DEFAUT = "MAD"


def centimes_vers_dirhams(cents: int) -> Decimal:
    """Convertit un montant en centimes (entier) en dirhams exacts.

    Réservé à l'affichage et aux exports — jamais pour un calcul dont le
    résultat serait re-stocké en centimes.
    """
    if not isinstance(cents, int) or isinstance(cents, bool):
        raise TypeError(f"Un montant en centimes doit être un entier, reçu {cents!r}.")
    return (Decimal(cents) / CENTS_PAR_DIRHAM).quantize(Decimal("0.01"))


def dirhams_vers_centimes(dirhams: Decimal | str | int) -> int:
    """Convertit un montant en dirhams (saisie utilisateur, seed, fixture) en centimes.

    N'accepte ni `float` ni `bool` : un flottant introduirait une imprécision
    binaire (0.1 + 0.2 != 0.3) au moment précis où l'exactitude est requise.
    """
    if isinstance(dirhams, float) or isinstance(dirhams, bool):
        raise TypeError(
            f"Un montant en dirhams doit être un Decimal, une str ou un int, reçu {dirhams!r}."
        )
    montant = dirhams if isinstance(dirhams, Decimal) else Decimal(str(dirhams))
    centimes = (montant * CENTS_PAR_DIRHAM).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(centimes)


def formater_montant(cents: int, devise: str = DEVISE_PAR_DEFAUT) -> str:
    """Formate un montant en centimes pour affichage humain : « 12 345,50 MAD »."""
    dirhams = centimes_vers_dirhams(cents)
    signe = "-" if dirhams < 0 else ""
    entiers, decimales = f"{abs(dirhams):.2f}".split(".")
    return f"{signe}{_grouper_milliers(entiers)},{decimales} {devise}"


def _grouper_milliers(chiffres: str) -> str:
    """Insère une espace tous les trois chiffres, depuis la droite."""
    inverses = chiffres[::-1]
    groupes = [inverses[i : i + 3] for i in range(0, len(inverses), 3)]
    return " ".join(groupes)[::-1]
