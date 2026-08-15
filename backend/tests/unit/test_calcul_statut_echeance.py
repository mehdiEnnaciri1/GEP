"""Tests du calcul de statut d'échéance (§8.2 de docs/02-modele-donnees.md) —
pure, sans base. Recalculé À CHAQUE FOIS depuis (montant_du, montant_payé),
jamais par transition ad hoc : c'est ce qui rend l'annulation sûre (voir
tests/e2e/test_paiements.py, qui exerce ce même calcul après une annulation)."""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "cle-de-test-jamais-utilisee-en-production")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")

from app.modules.paiements.models import StatutEcheance  # noqa: E402
from app.modules.paiements.service import calculer_statut_echeance  # noqa: E402


class TestCalculerStatutEcheance:
    def test_rien_paye(self):
        assert calculer_statut_echeance(montant_du_cents=30000, montant_paye_cents=0) == (
            StatutEcheance.NON_PAYE
        )

    def test_paiement_partiel(self):
        assert (
            calculer_statut_echeance(montant_du_cents=30000, montant_paye_cents=10000)
            == StatutEcheance.PARTIEL
        )

    def test_paiement_exact(self):
        assert (
            calculer_statut_echeance(montant_du_cents=30000, montant_paye_cents=30000)
            == StatutEcheance.PAYE
        )

    def test_trop_percu_reste_paye(self):
        """§8.2 : le trop-perçu (payé > dû) est autorisé, statut PAYE."""
        assert (
            calculer_statut_echeance(montant_du_cents=30000, montant_paye_cents=35000)
            == StatutEcheance.PAYE
        )

    def test_echeance_a_montant_du_nul(self):
        # Cas limite : zéro élève sur une affectation / montant dû nul.
        assert (
            calculer_statut_echeance(montant_du_cents=0, montant_paye_cents=0)
            == StatutEcheance.NON_PAYE
        )
