"""Exceptions métier et leur traduction en réponses HTTP.

Un service ne lève jamais `HTTPException` (voir §3 de `docs/01-architecture.md`) :
il lève une des exceptions ci-dessous, que `enregistrer_gestionnaires_exceptions`
traduit en réponse JSON. Les modules définissent leurs propres exceptions en
héritant de ces quatre catégories, jamais de `ErreurMetier` directement.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class ErreurMetier(Exception):
    """Base de toute exception métier. Ne pas lever directement : hériter d'une des
    quatre catégories ci-dessous, chacune associée à un code HTTP fixe."""

    code_http: int

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class RessourceIntrouvable(ErreurMetier):
    """La ressource demandée n'existe pas. Ex. : `EleveIntrouvable`."""

    code_http = status.HTTP_404_NOT_FOUND


class ConflitMetier(ErreurMetier):
    """L'opération contredit une règle d'unicité ou d'état. Ex. : `PaieDejaValidee`,
    `AffectationDejaAttribuee`."""

    code_http = status.HTTP_409_CONFLICT


class ValidationMetier(ErreurMetier):
    """Les données sont syntaxiquement valides mais métier-ment incorrectes.
    Ex. : `MontantInvalide`."""

    code_http = status.HTTP_422_UNPROCESSABLE_CONTENT


class OperationNonAutorisee(ErreurMetier):
    """L'utilisateur a le rôle requis mais l'opération lui est interdite sur cette
    ressource précise (distinct du contrôle de rôle porté par la route elle-même)."""

    code_http = status.HTTP_403_FORBIDDEN


class AuthentificationInvalide(ErreurMetier):
    """Identifiants incorrects, jeton absent, invalide ou expiré. Distinct
    d'`OperationNonAutorisee` (403) : ici, l'identité elle-même n'est pas établie."""

    code_http = status.HTTP_401_UNAUTHORIZED


def enregistrer_gestionnaires_exceptions(app: FastAPI) -> None:
    """Branche les catégories d'exceptions métier sur des réponses JSON.

    À appeler une fois depuis `main.py` à la création de l'application.
    """

    for categorie in (
        RessourceIntrouvable,
        ConflitMetier,
        ValidationMetier,
        OperationNonAutorisee,
        AuthentificationInvalide,
    ):
        app.add_exception_handler(categorie, _gestionnaire)


async def _gestionnaire(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ErreurMetier)
    return JSONResponse(status_code=exc.code_http, content={"detail": exc.message})
