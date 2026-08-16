"""Tests unitaires de app/shared/stockage.py — détection MIME sur les octets
réels, garde contre le path traversal, limite de taille. Purs, sans base de
données : `base_dir` est injecté (répertoire temporaire), jamais le vrai
`reglages.chemin_justificatifs`."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import ValidationMetier
from app.shared import stockage

JPEG_MINIMAL = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG_MINIMAL = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
PDF_MINIMAL = b"%PDF-1.4\n" + b"\x00" * 20


class TestDetecterTypeMime:
    def test_jpeg(self):
        assert stockage.detecter_type_mime(JPEG_MINIMAL) == "image/jpeg"

    def test_png(self):
        assert stockage.detecter_type_mime(PNG_MINIMAL) == "image/png"

    def test_pdf(self):
        assert stockage.detecter_type_mime(PDF_MINIMAL) == "application/pdf"

    def test_type_inconnu(self):
        assert stockage.detecter_type_mime(b"contenu quelconque") is None

    def test_extension_mensongere_ne_suffit_pas(self):
        # Un fichier .jpg dont le contenu n'est pas réellement un JPEG doit
        # être détecté comme inconnu — seule la signature binaire compte.
        assert stockage.detecter_type_mime(b"<html>faux jpeg</html>") is None


class TestSauvegarder:
    def test_sauvegarde_un_jpeg_valide(self, tmp_path: Path):
        type_mime = stockage.sauvegarder(JPEG_MINIMAL, "charges/photo.jpg", base_dir=tmp_path)
        assert type_mime == "image/jpeg"
        assert (tmp_path / "charges" / "photo.jpg").read_bytes() == JPEG_MINIMAL

    def test_refuse_un_type_non_reconnu(self, tmp_path: Path):
        with pytest.raises(ValidationMetier):
            stockage.sauvegarder(b"pas une image", "charges/x.jpg", base_dir=tmp_path)

    def test_refuse_un_fichier_trop_volumineux(self, tmp_path: Path, monkeypatch):
        from app.core import config

        config.obtenir_reglages.cache_clear()
        monkeypatch.setenv("TAILLE_MAX_FICHIER_MO", "0")
        try:
            with pytest.raises(ValidationMetier):
                stockage.sauvegarder(JPEG_MINIMAL, "charges/x.jpg", base_dir=tmp_path)
        finally:
            config.obtenir_reglages.cache_clear()

    def test_refuse_un_chemin_qui_sort_du_repertoire(self, tmp_path: Path):
        """Path traversal : `../../evil.txt` doit être refusé même si le
        contenu est un type de fichier valide — la garde porte sur le
        CHEMIN, indépendamment du contenu."""
        with pytest.raises(ValidationMetier):
            stockage.sauvegarder(JPEG_MINIMAL, "../../evil.txt", base_dir=tmp_path)

        # Rien n'a été écrit en dehors de tmp_path.
        assert not (tmp_path.parent.parent / "evil.txt").exists()

    def test_refuse_un_chemin_absolu_detourne(self, tmp_path: Path):
        with pytest.raises(ValidationMetier):
            stockage.sauvegarder(JPEG_MINIMAL, "/etc/passwd", base_dir=tmp_path)


class TestLire:
    def test_relit_ce_qui_a_ete_sauvegarde(self, tmp_path: Path):
        stockage.sauvegarder(PDF_MINIMAL, "charges/justificatif.pdf", base_dir=tmp_path)
        assert stockage.lire("charges/justificatif.pdf", base_dir=tmp_path) == PDF_MINIMAL

    def test_refuse_un_chemin_qui_sort_du_repertoire(self, tmp_path: Path):
        with pytest.raises(ValidationMetier):
            stockage.lire("../../etc/passwd", base_dir=tmp_path)
