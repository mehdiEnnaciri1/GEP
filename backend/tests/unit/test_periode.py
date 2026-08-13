"""Tests de shared/periode.py."""

from datetime import date

import pytest

from app.shared.periode import (
    depuis_date,
    dernier_jour,
    periode_courante,
    periode_precedente,
    periode_suivante,
    premier_jour,
    valider_periode,
)


class TestValiderPeriode:
    @pytest.mark.parametrize("periode", ["2025-01", "2025-12", "1999-06"])
    def test_formats_valides(self, periode):
        valider_periode(periode)  # ne lève pas

    @pytest.mark.parametrize(
        "periode",
        [
            "2025-13",
            "2025-00",
            "25-10",
            "2025/10",
            "2025-1",
            "2025-010",
            "",
            "abcd-ef",
        ],
    )
    def test_formats_invalides(self, periode):
        with pytest.raises(ValueError):
            valider_periode(periode)


class TestPremierEtDernierJour:
    def test_premier_jour(self):
        assert premier_jour("2025-10") == date(2025, 10, 1)

    def test_dernier_jour_mois_a_31_jours(self):
        assert dernier_jour("2025-10") == date(2025, 10, 31)

    def test_dernier_jour_mois_a_30_jours(self):
        assert dernier_jour("2025-11") == date(2025, 11, 30)

    def test_dernier_jour_fevrier_annee_non_bissextile(self):
        assert dernier_jour("2025-02") == date(2025, 2, 28)

    def test_dernier_jour_fevrier_annee_bissextile(self):
        assert dernier_jour("2024-02") == date(2024, 2, 29)

    def test_rejette_une_periode_invalide(self):
        with pytest.raises(ValueError):
            premier_jour("2025-13")


class TestPeriodeSuivanteEtPrecedente:
    def test_periode_suivante_meme_annee(self):
        assert periode_suivante("2025-10") == "2025-11"

    def test_periode_suivante_change_annee(self):
        assert periode_suivante("2025-12") == "2026-01"

    def test_periode_precedente_meme_annee(self):
        assert periode_precedente("2025-10") == "2025-09"

    def test_periode_precedente_change_annee(self):
        assert periode_precedente("2025-01") == "2024-12"

    def test_aller_retour(self):
        assert periode_precedente(periode_suivante("2025-06")) == "2025-06"


class TestDepuisDate:
    def test_depuis_date(self):
        assert depuis_date(date(2025, 11, 5)) == "2025-11"

    def test_depuis_date_premier_du_mois(self):
        assert depuis_date(date(2025, 1, 1)) == "2025-01"


class TestPeriodeCourante:
    def test_format_valide(self):
        periode = periode_courante()
        valider_periode(periode)  # ne lève pas

    def test_coherente_avec_depuis_date(self):
        from datetime import datetime

        from app.shared.periode import FUSEAU_HORAIRE_CENTRE

        aujourdhui = datetime.now(FUSEAU_HORAIRE_CENTRE).date()
        assert periode_courante() == depuis_date(aujourdhui)
