"""Tests de app/core/security.py — hachage Argon2id et JWT, sans base de données."""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("SECRET_KEY", "cle-de-test-jamais-utilisee-en-production")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")

from app.core.exceptions import AuthentificationInvalide  # noqa: E402
from app.core.security import (  # noqa: E402
    creer_access_token,
    creer_refresh_token,
    decoder_token,
    hacher_mot_de_passe,
    verifier_mot_de_passe,
)


class TestHachageMotDePasse:
    def test_hash_different_du_mot_de_passe(self):
        assert hacher_mot_de_passe("secret123") != "secret123"

    def test_verifie_le_bon_mot_de_passe(self):
        hash_ = hacher_mot_de_passe("secret123")
        assert verifier_mot_de_passe("secret123", hash_) is True

    def test_refuse_le_mauvais_mot_de_passe(self):
        hash_ = hacher_mot_de_passe("secret123")
        assert verifier_mot_de_passe("autre-chose", hash_) is False

    def test_refuse_quand_aucun_hash_stocke(self):
        # Simule un email inexistant : ne doit ni lever, ni renvoyer True.
        assert verifier_mot_de_passe("peu-importe", None) is False

    def test_deux_hash_du_meme_mot_de_passe_sont_differents(self):
        # Sel aléatoire par hachage — propriété de base d'Argon2.
        assert hacher_mot_de_passe("secret123") != hacher_mot_de_passe("secret123")


class TestJetons:
    def test_access_token_se_decode(self):
        jeton = creer_access_token(utilisateur_id=42, role="ADMIN")
        charge = decoder_token(jeton, type_attendu="access")
        assert charge["sub"] == "42"
        assert charge["role"] == "ADMIN"
        assert charge["type"] == "access"

    def test_refresh_token_se_decode(self):
        jeton = creer_refresh_token(utilisateur_id=7)
        charge = decoder_token(jeton, type_attendu="refresh")
        assert charge["sub"] == "7"
        assert charge["type"] == "refresh"

    def test_refresh_token_n_a_pas_de_role(self):
        jeton = creer_refresh_token(utilisateur_id=7)
        charge = decoder_token(jeton, type_attendu="refresh")
        assert "role" not in charge

    def test_refresh_token_porte_un_iat(self):
        # `iat` sert à la révocation (AuthService.rafraichir compare cette
        # date à `utilisateur.tokens_invalides_avant`, voir étape 10).
        avant = time.time()
        jeton = creer_refresh_token(utilisateur_id=7)
        charge = decoder_token(jeton, type_attendu="refresh")
        assert "iat" in charge
        assert avant - 1 <= charge["iat"] <= time.time() + 1

    def test_refuse_un_access_token_presente_comme_refresh(self):
        jeton = creer_access_token(utilisateur_id=42, role="ADMIN")
        with pytest.raises(AuthentificationInvalide):
            decoder_token(jeton, type_attendu="refresh")

    def test_refuse_un_refresh_token_presente_comme_access(self):
        jeton = creer_refresh_token(utilisateur_id=42)
        with pytest.raises(AuthentificationInvalide):
            decoder_token(jeton, type_attendu="access")

    def test_refuse_un_jeton_invalide(self):
        with pytest.raises(AuthentificationInvalide):
            decoder_token("ceci-nest-pas-un-jwt", type_attendu="access")

    def test_refuse_un_jeton_signe_avec_une_autre_cle(self):
        from jose import jwt

        jeton = jwt.encode(
            {"sub": "1", "type": "access", "exp": time.time() + 3600},
            "une-autre-cle-secrete",
            algorithm="HS256",
        )
        with pytest.raises(AuthentificationInvalide):
            decoder_token(jeton, type_attendu="access")

    def test_refuse_un_jeton_expire(self):
        from jose import jwt

        jeton = jwt.encode(
            {"sub": "1", "type": "access", "exp": time.time() - 10},
            os.environ["SECRET_KEY"],
            algorithm="HS256",
        )
        with pytest.raises(AuthentificationInvalide):
            decoder_token(jeton, type_attendu="access")
