"""Génération des rapports PDF (Jinja2 + WeasyPrint).

⚠ `weasyprint` est importé EN PARESSEUX, à l'intérieur de `_rendre`, jamais
au niveau du module (voir docs/adr/2026-08-13-weasyprint-extra-optionnel.md
et docs/adr/2026-08-14-choix-etape-6-a-9.md) : WeasyPrint dépend de
bibliothèques natives (Pango, Cairo, GDK-Pixbuf) absentes d'un poste Windows
sans le runtime GTK. Importer ce module (schémas, service, router) doit
rester possible partout ; seul l'appel réel à une fonction `pdf_*` exige
l'environnement Docker.

Les gabarits (`templates/*.html`) référencent "Noto Sans Arabic" /
"Noto Naskh Arabic" dans leur pile de polices — installées dans l'image via
`fonts-noto-core` (voir backend/Dockerfile) — pour que les noms arabes des
élèves et professeurs s'affichent correctement, pas en caractères manquants.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_REPERTOIRE_TEMPLATES = Path(__file__).parent / "templates"

_environnement = Environment(
    loader=FileSystemLoader(str(_REPERTOIRE_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)


def _rendre(nom_gabarit: str, **contexte: object) -> bytes:
    import weasyprint  # import paresseux — voir docstring du module

    html = _environnement.get_template(nom_gabarit).render(**contexte)
    return bytes(weasyprint.HTML(string=html).write_pdf())


class Colonne:
    def __init__(self, cle: str, libelle: str, *, montant: bool = False) -> None:
        self.cle = cle
        self.libelle = libelle
        self.montant = montant


def pdf_tableau(
    *,
    titre: str,
    sous_titre: str | None,
    colonnes: list[Colonne],
    lignes: list[dict[str, object]],
    totaux: list[dict[str, object]] | None = None,
) -> bytes:
    return _rendre(
        "tableau.html",
        titre=titre,
        sous_titre=sous_titre,
        colonnes=colonnes,
        lignes=lignes,
        totaux=totaux,
    )


def pdf_recu(
    *,
    nom_centre: str,
    numero_recu: str,
    eleve_nom: str,
    eleve_prenom: str,
    eleve_matricule: str,
    type_libelle: str,
    periode: str | None,
    date_paiement: str,
    mode_paiement: str,
    montant: str,
) -> bytes:
    return _rendre(
        "recu.html",
        nom_centre=nom_centre,
        numero_recu=numero_recu,
        eleve_nom=eleve_nom,
        eleve_prenom=eleve_prenom,
        eleve_matricule=eleve_matricule,
        type_libelle=type_libelle,
        periode=periode,
        date_paiement=date_paiement,
        mode_paiement=mode_paiement,
        montant=montant,
    )
