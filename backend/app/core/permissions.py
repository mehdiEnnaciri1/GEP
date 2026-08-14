"""Dépendances FastAPI d'authentification et d'autorisation.

Toute route porte une dépendance explicite : `Depends(obtenir_utilisateur_courant)`
pour « authentifié, peu importe le rôle », `Depends(exige_role(...))` pour un
ou plusieurs rôles précis. Jamais de vérification de rôle dans le corps d'un
handler (voir §Permissions de CLAUDE.md).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthentificationInvalide, OperationNonAutorisee
from app.core.security import decoder_token
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.auth.repository import UtilisateurRepository

_schema_bearer = HTTPBearer(auto_error=False)


async def obtenir_utilisateur_courant(
    identifiants: HTTPAuthorizationCredentials | None = Depends(_schema_bearer),
    session: AsyncSession = Depends(get_session),
) -> Utilisateur:
    if identifiants is None:
        raise AuthentificationInvalide("Authentification requise.")

    charge = decoder_token(identifiants.credentials, type_attendu="access")
    utilisateur = await UtilisateurRepository(session).get_by_id(int(charge["sub"]))

    if utilisateur is None or not utilisateur.actif:
        raise AuthentificationInvalide("Authentification requise.")

    return utilisateur


def exige_role(*roles: RoleUtilisateur) -> Callable[..., Coroutine[Any, Any, Utilisateur]]:
    async def dependance(
        utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    ) -> Utilisateur:
        if utilisateur.role not in roles:
            raise OperationNonAutorisee("Rôle insuffisant pour cette opération.")
        return utilisateur

    return dependance
