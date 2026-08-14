"""Endpoints HTTP du module auth — validation d'entrée et permissions uniquement,
aucune règle métier (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obtenir_reglages
from app.core.exceptions import AuthentificationInvalide
from app.core.permissions import exige_role, obtenir_utilisateur_courant
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.auth.repository import UtilisateurRepository
from app.modules.auth.schemas import (
    AccessTokenReponse,
    LoginReponse,
    LoginRequete,
    UtilisateurPublic,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_NOM_COOKIE_REFRESH = "refresh_token"
_CHEMIN_COOKIE_REFRESH = "/api/auth"


def _adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _poser_cookie_refresh(response: Response, refresh_token: str) -> None:
    reglages = obtenir_reglages()
    response.set_cookie(
        key=_NOM_COOKIE_REFRESH,
        value=refresh_token,
        max_age=reglages.refresh_token_jours * 86400,
        path=_CHEMIN_COOKIE_REFRESH,
        httponly=True,
        samesite="strict",
        secure=reglages.app_env != "development",
    )


@router.post("/login", response_model=LoginReponse)
async def login(
    donnees: LoginRequete,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> LoginReponse:
    service = AuthService(session)
    access_token, refresh_token, utilisateur = await service.authentifier(
        donnees.email, donnees.mot_de_passe, _adresse_ip(request)
    )
    _poser_cookie_refresh(response, refresh_token)
    return LoginReponse(
        access_token=access_token, utilisateur=UtilisateurPublic.model_validate(utilisateur)
    )


@router.post("/refresh", response_model=AccessTokenReponse)
async def refresh(
    request: Request, session: AsyncSession = Depends(get_session)
) -> AccessTokenReponse:
    refresh_token = request.cookies.get(_NOM_COOKIE_REFRESH)
    if refresh_token is None:
        raise AuthentificationInvalide("Authentification requise.")

    access_token = await AuthService(session).rafraichir(refresh_token)
    return AccessTokenReponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    session: AsyncSession = Depends(get_session),
) -> None:
    await AuthService(session).deconnecter(utilisateur, _adresse_ip(request))
    response.delete_cookie(_NOM_COOKIE_REFRESH, path=_CHEMIN_COOKIE_REFRESH)


@router.get("/me", response_model=UtilisateurPublic)
async def me(utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant)) -> UtilisateurPublic:
    return UtilisateurPublic.model_validate(utilisateur)


@router.get("/utilisateurs", response_model=list[UtilisateurPublic])
async def lister_utilisateurs(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(exige_role(RoleUtilisateur.ADMIN)),
) -> list[UtilisateurPublic]:
    utilisateurs = await UtilisateurRepository(session).lister()
    return [UtilisateurPublic.model_validate(u) for u in utilisateurs]
