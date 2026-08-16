"""Service du module rapports — lecture seule, compose les données des
autres modules puis délègue le rendu à pdf.py / excel.py. Aucun commit ici :
générer un rapport n'écrit rien."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RessourceIntrouvable
from app.modules.eleves.repository import EleveRepository
from app.modules.paie.models import StatutPaie
from app.modules.paie.repository import PaieMensuelleRepository
from app.modules.paiements.models import TypePaiement
from app.modules.paiements.repository import EcheanceRepository, PaiementRepository
from app.modules.professeurs.repository import ProfesseurRepository
from app.modules.rapports import excel, pdf
from app.modules.rapports.pdf import Colonne
from app.modules.referentiel.repository import NiveauRepository, ParametreRepository
from app.shared.money import formater_montant

_COLONNES_ELEVES = [
    Colonne("matricule", "Matricule"),
    Colonne("nom", "Nom et prénom"),
    Colonne("niveau", "Niveau"),
    Colonne("statut", "Statut"),
]
_COLONNES_PAIEMENTS = [
    Colonne("numero_recu", "Reçu"),
    Colonne("date", "Date"),
    Colonne("eleve", "Élève"),
    Colonne("type", "Type"),
    Colonne("montant", "Montant", montant=True),
    Colonne("mode", "Mode"),
    Colonne("statut", "Statut"),
]
_COLONNES_IMPAYES = [
    Colonne("eleve", "Élève"),
    Colonne("matricule", "Matricule"),
    Colonne("du", "Dû", montant=True),
    Colonne("paye", "Payé", montant=True),
    Colonne("reste", "Reste", montant=True),
    Colonne("statut", "Statut"),
]
_COLONNES_PAIE = [
    Colonne("professeur", "Professeur"),
    Colonne("total", "Total", montant=True),
    Colonne("statut", "Statut"),
]


class RapportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._eleves = EleveRepository(session)
        self._niveaux = NiveauRepository(session)
        self._paiements = PaiementRepository(session)
        self._echeances = EcheanceRepository(session)
        self._professeurs = ProfesseurRepository(session)
        self._paies = PaieMensuelleRepository(session)
        self._parametres = ParametreRepository(session)

    async def _libelles_niveaux(self) -> dict[str, str]:
        return {n.code: n.libelle for n in await self._niveaux.lister()}

    async def _nom_centre(self) -> str:
        parametre = await self._parametres.get_by_cle("nom_centre")
        return parametre.valeur if parametre is not None else "Centre"

    # ---- Liste des élèves ----------------------------------------------------

    async def _lignes_eleves(self) -> list[dict[str, object]]:
        libelles_niveaux = await self._libelles_niveaux()
        elements, _ = await self._eleves.lister(
            recherche=None, niveau_code=None, statut=None, page=1, taille=100000
        )
        return [
            {
                "matricule": e.matricule,
                "nom": f"{e.prenom} {e.nom}",
                "niveau": libelles_niveaux.get(e.niveau_code, e.niveau_code),
                "statut": e.statut.value,
            }
            for e in elements
        ]

    async def pdf_liste_eleves(self) -> bytes:
        return pdf.pdf_tableau(
            titre="Liste des élèves",
            sous_titre=None,
            colonnes=_COLONNES_ELEVES,
            lignes=await self._lignes_eleves(),
        )

    async def excel_liste_eleves(self) -> bytes:
        return excel.excel_tableau(
            titre="Liste des élèves", colonnes=_COLONNES_ELEVES, lignes=await self._lignes_eleves()
        )

    # ---- Paiements sur une période --------------------------------------------

    async def _lignes_paiements(self, periode: str) -> tuple[list[dict[str, object]], int]:
        paiements = await self._paiements.lister_par_periode(periode)
        lignes: list[dict[str, object]] = []
        total = 0
        for p in paiements:
            eleve = await self._eleves.get_by_id(p.eleve_id)
            assert eleve is not None
            lignes.append(
                {
                    "numero_recu": p.numero_recu,
                    "date": p.date_paiement.isoformat(),
                    "eleve": f"{eleve.prenom} {eleve.nom}",
                    "type": p.type.value,
                    "montant": formater_montant(p.montant_cents),
                    "mode": p.mode.value,
                    "statut": "Annulé" if p.annule_le is not None else "Actif",
                }
            )
            if p.annule_le is None:
                total += p.montant_cents
        return lignes, total

    async def pdf_liste_paiements(self, periode: str) -> bytes:
        lignes, total = await self._lignes_paiements(periode)
        return pdf.pdf_tableau(
            titre="Paiements",
            sous_titre=f"Période {periode}",
            colonnes=_COLONNES_PAIEMENTS,
            lignes=lignes,
            totaux=[
                {"valeur": "Total (hors annulés)"},
                {"valeur": ""},
                {"valeur": ""},
                {"valeur": formater_montant(total), "montant": True},
                {"valeur": ""},
                {"valeur": ""},
            ],
        )

    async def excel_liste_paiements(self, periode: str) -> bytes:
        lignes, _ = await self._lignes_paiements(periode)
        return excel.excel_tableau(
            titre=f"Paiements {periode}", colonnes=_COLONNES_PAIEMENTS, lignes=lignes
        )

    # ---- Impayés ---------------------------------------------------------------

    async def _lignes_impayes(self, periode: str) -> tuple[list[dict[str, object]], int]:
        echeances = await self._echeances.lister_impayes(periode)
        lignes: list[dict[str, object]] = []
        total = 0
        for echeance in echeances:
            eleve = await self._eleves.get_by_id(echeance.eleve_id)
            assert eleve is not None
            reste = echeance.montant_du_cents - echeance.montant_paye_cents
            lignes.append(
                {
                    "eleve": f"{eleve.prenom} {eleve.nom}",
                    "matricule": eleve.matricule,
                    "du": formater_montant(echeance.montant_du_cents),
                    "paye": formater_montant(echeance.montant_paye_cents),
                    "reste": formater_montant(reste),
                    "statut": echeance.statut.value,
                }
            )
            total += reste
        return lignes, total

    async def pdf_liste_impayes(self, periode: str) -> bytes:
        lignes, total = await self._lignes_impayes(periode)
        return pdf.pdf_tableau(
            titre="Impayés",
            sous_titre=f"Période {periode}",
            colonnes=_COLONNES_IMPAYES,
            lignes=lignes,
            totaux=[
                {"valeur": "Total"},
                {"valeur": ""},
                {"valeur": ""},
                {"valeur": ""},
                {"valeur": formater_montant(total), "montant": True},
                {"valeur": ""},
            ],
        )

    async def excel_liste_impayes(self, periode: str) -> bytes:
        lignes, _ = await self._lignes_impayes(periode)
        return excel.excel_tableau(
            titre=f"Impayes {periode}", colonnes=_COLONNES_IMPAYES, lignes=lignes
        )

    # ---- Paie des professeurs ----------------------------------------------------

    async def _lignes_paie(self, periode: str) -> tuple[list[dict[str, object]], int]:
        paies = await self._paies.lister_par_periode(periode)
        lignes: list[dict[str, object]] = []
        total = 0
        for paie in paies:
            professeur = await self._professeurs.get_by_id(paie.professeur_id)
            assert professeur is not None
            lignes.append(
                {
                    "professeur": f"{professeur.prenom} {professeur.nom}",
                    "total": formater_montant(paie.total_cents),
                    "statut": paie.statut.value,
                }
            )
            if paie.statut != StatutPaie.BROUILLON:
                total += paie.total_cents
        return lignes, total

    async def pdf_paie_professeurs(self, periode: str) -> bytes:
        lignes, total = await self._lignes_paie(periode)
        return pdf.pdf_tableau(
            titre="Paie des professeurs",
            sous_titre=f"Période {periode}",
            colonnes=_COLONNES_PAIE,
            lignes=lignes,
            totaux=[
                {"valeur": "Total (hors brouillon)"},
                {"valeur": formater_montant(total), "montant": True},
                {"valeur": ""},
            ],
        )

    async def excel_paie_professeurs(self, periode: str) -> bytes:
        lignes, _ = await self._lignes_paie(periode)
        return excel.excel_tableau(titre=f"Paie {periode}", colonnes=_COLONNES_PAIE, lignes=lignes)

    # ---- Récapitulatif mensuel ----------------------------------------------------

    async def _paires_recapitulatif(self, periode: str) -> list[tuple[str, str]]:
        from app.modules.dashboard.service import DashboardService

        indicateurs = await DashboardService(self._session).indicateurs_complets(periode)
        paires = [
            ("Période", indicateurs.periode),
            ("Nombre d'élèves", str(indicateurs.nombre_eleves_total)),
            ("Nombre de professeurs", str(indicateurs.nombre_professeurs)),
            (
                "Encaissé (mensualités + inscriptions)",
                formater_montant(indicateurs.montant_total_encaisse_cents),
            ),
            (
                "Frais d'inscription cumulés",
                formater_montant(indicateurs.montant_frais_inscription_cumules_cents),
            ),
            ("Impayés", formater_montant(indicateurs.montant_impayes_cents)),
            ("Charges", formater_montant(indicateurs.total_charges_cents)),
            ("Paie (hors brouillon)", formater_montant(indicateurs.total_paie_cents)),
            ("Bénéfice net", formater_montant(indicateurs.benefice_net_cents)),
        ]
        libelles_niveaux = await self._libelles_niveaux()
        for niveau in indicateurs.nombre_eleves_par_niveau:
            paires.append(
                (
                    f"Élèves — {libelles_niveaux.get(niveau.niveau_code, niveau.niveau_code)}",
                    str(niveau.nombre),
                )
            )
        return paires

    async def pdf_recapitulatif(self, periode: str) -> bytes:
        paires = await self._paires_recapitulatif(periode)
        return pdf.pdf_tableau(
            titre="Récapitulatif mensuel",
            sous_titre=f"Période {periode}",
            colonnes=[Colonne("cle", "Indicateur"), Colonne("valeur", "Valeur")],
            lignes=[{"cle": libelle, "valeur": valeur} for libelle, valeur in paires],
        )

    async def excel_recapitulatif(self, periode: str) -> bytes:
        return excel.excel_cle_valeur(
            titre=f"Recap {periode}", paires=await self._paires_recapitulatif(periode)
        )

    # ---- Reçu individuel -----------------------------------------------------------

    async def pdf_recu(self, paiement_id: int) -> bytes:
        paiement = await self._paiements.get_by_id(paiement_id)
        if paiement is None:
            raise RessourceIntrouvable(f"Paiement {paiement_id} introuvable.")
        eleve = await self._eleves.get_by_id(paiement.eleve_id)
        assert eleve is not None
        type_libelle = "Mensualité" if paiement.type == TypePaiement.MENSUALITE else "Inscription"

        return pdf.pdf_recu(
            nom_centre=await self._nom_centre(),
            numero_recu=paiement.numero_recu,
            eleve_nom=eleve.nom,
            eleve_prenom=eleve.prenom,
            eleve_matricule=eleve.matricule,
            type_libelle=type_libelle,
            periode=paiement.periode,
            date_paiement=paiement.date_paiement.isoformat(),
            mode_paiement=paiement.mode.value,
            montant=formater_montant(paiement.montant_cents),
        )


__all__ = ["RapportService"]
