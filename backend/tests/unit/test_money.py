"""Tests de shared/money.py — module le plus utilisé et le plus dangereux s'il est faux."""

from decimal import Decimal

import pytest

from app.shared.money import (
    centimes_vers_dirhams,
    dirhams_vers_centimes,
    formater_montant,
)

# formater_montant sépare les groupes de milliers et le code devise par une
# espace insécable, pour qu'un export PDF ne coupe jamais "50,00" et "MAD"
# sur deux lignes.
ESPACE_INSECABLE = " "


class TestCentimesVersDirhams:
    def test_montant_rond(self):
        assert centimes_vers_dirhams(5000) == Decimal("50.00")

    def test_montant_avec_centimes(self):
        assert centimes_vers_dirhams(150) == Decimal("1.50")

    def test_zero(self):
        assert centimes_vers_dirhams(0) == Decimal("0.00")

    def test_montant_negatif(self):
        assert centimes_vers_dirhams(-500) == Decimal("-5.00")

    def test_refuse_un_flottant(self):
        with pytest.raises(TypeError):
            centimes_vers_dirhams(50.0)  # type: ignore[arg-type]

    def test_refuse_un_booleen(self):
        with pytest.raises(TypeError):
            centimes_vers_dirhams(True)  # type: ignore[arg-type]

    def test_refuse_une_chaine(self):
        with pytest.raises(TypeError):
            centimes_vers_dirhams("5000")  # type: ignore[arg-type]


class TestDirhamsVersCentimes:
    def test_depuis_une_chaine(self):
        assert dirhams_vers_centimes("50") == 5000

    def test_depuis_un_decimal(self):
        assert dirhams_vers_centimes(Decimal("35.50")) == 3550

    def test_depuis_un_entier(self):
        assert dirhams_vers_centimes(50) == 5000

    def test_arrondi_demi_centime_vers_le_haut(self):
        # 0.005 DH = 0,5 centime, arrondi à 1 (ROUND_HALF_UP)
        assert dirhams_vers_centimes("0.005") == 1

    def test_arrondi_troisieme_decimale(self):
        assert dirhams_vers_centimes("35.999") == 3600

    def test_refuse_un_flottant(self):
        with pytest.raises(TypeError):
            dirhams_vers_centimes(50.0)  # type: ignore[arg-type]

    def test_refuse_un_booleen(self):
        with pytest.raises(TypeError):
            dirhams_vers_centimes(True)  # type: ignore[arg-type]

    def test_aller_retour_exact(self):
        cents = dirhams_vers_centimes("35.50")
        assert centimes_vers_dirhams(cents) == Decimal("35.50")


class TestFormaterMontant:
    def test_montant_simple(self):
        assert formater_montant(5000) == f"50,00{ESPACE_INSECABLE}MAD"

    def test_montant_avec_milliers(self):
        assert (
            formater_montant(1_234_550)
            == f"12{ESPACE_INSECABLE}345,50{ESPACE_INSECABLE}MAD"
        )

    def test_montant_negatif(self):
        assert formater_montant(-5000) == f"-50,00{ESPACE_INSECABLE}MAD"

    def test_zero(self):
        assert formater_montant(0) == f"0,00{ESPACE_INSECABLE}MAD"

    def test_devise_personnalisee(self):
        assert formater_montant(5000, devise="EUR") == f"50,00{ESPACE_INSECABLE}EUR"

    def test_frais_inscription_reference(self):
        # Les frais d'inscription du référentiel : 5000 centimes = 50 DH (§3.1)
        assert formater_montant(5000) == f"50,00{ESPACE_INSECABLE}MAD"

    def test_exemple_paie_section_7_2(self):
        # 1BAC/Math/12 élèves = 300 DH, 2BAC/Math/15 élèves = 450 DH, total 750 DH
        assert formater_montant(75_000) == f"750,00{ESPACE_INSECABLE}MAD"
