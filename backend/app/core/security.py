"""Hachage des mots de passe (Argon2id) et JWT (accès court + rafraîchissement)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import obtenir_reglages
from app.core.exceptions import AuthentificationInvalide

_ALGORITHME = "HS256"
_hacheur = PasswordHasher()

# Hash valide d'un mot de passe arbitraire, jamais attribué à un compte réel.
# Sert à faire tourner `verify` même quand l'utilisateur n'existe pas, pour
# qu'une tentative de connexion sur un email inexistant prenne le même temps
# qu'un mauvais mot de passe — ne pas laisser le temps de réponse révéler si
# un email est enregistré.
_HASH_LEURRE = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "axeUPl4XkS6r/HrbiGezYg$EgqlG+o6BnmEgqkfEaEBKzLysGAXUIMjx0ygwCmZrhA"
)


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str | None) -> bool:
    """`hash_stocke=None` : fait tourner Argon2 contre un hash leurre, pour ne pas
    révéler par le temps de réponse qu'aucun compte ne correspond."""

    try:
        _hacheur.verify(hash_stocke or _HASH_LEURRE, mot_de_passe)
        return hash_stocke is not None
    except VerifyMismatchError:
        return False


def creer_access_token(utilisateur_id: int, role: str) -> str:
    reglages = obtenir_reglages()
    expiration = datetime.now(UTC) + timedelta(minutes=reglages.access_token_minutes)
    return _encoder(sub=str(utilisateur_id), role=role, type_jeton="access", expiration=expiration)


def creer_refresh_token(utilisateur_id: int) -> str:
    reglages = obtenir_reglages()
    expiration = datetime.now(UTC) + timedelta(days=reglages.refresh_token_jours)
    return _encoder(sub=str(utilisateur_id), role=None, type_jeton="refresh", expiration=expiration)


def _encoder(
    *, sub: str, role: str | None, type_jeton: Literal["access", "refresh"], expiration: datetime
) -> str:
    charge = {"sub": sub, "type": type_jeton, "exp": expiration}
    if role is not None:
        charge["role"] = role
    return jwt.encode(charge, obtenir_reglages().secret_key, algorithm=_ALGORITHME)


def decoder_token(jeton: str, type_attendu: Literal["access", "refresh"]) -> dict[str, Any]:
    """Lève `AuthentificationInvalide` (401) si le jeton est absent, malformé,
    expiré, ou n'est pas du type attendu (un refresh token ne doit jamais
    servir d'access token, et réciproquement)."""

    try:
        charge = jwt.decode(jeton, obtenir_reglages().secret_key, algorithms=[_ALGORITHME])
    except JWTError as exc:
        raise AuthentificationInvalide("Jeton invalide ou expiré.") from exc

    if charge.get("type") != type_attendu:
        raise AuthentificationInvalide("Jeton invalide ou expiré.")

    return charge
