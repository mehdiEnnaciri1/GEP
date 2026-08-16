"""Endpoints HTTP du module dashboard. Voir §6.6 de docs/01-architecture.md :
« Dashboard — Complet (ADMIN) / Vue restreinte, sans bénéfice ni charges
(CAISSIER) / Aucun (PROFESSEUR) ». Le point sensible (CLAUDE.md) : le
caissier ne doit voir ni charges, ni paie, ni bénéfice net — deux endpoints
séparés (`/restreint`, `/complet`), pas un filtrage du même endpoint côté
client."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.dashboard.schemas import IndicateursComplets, IndicateursRestreints
from app.modules.dashboard.service import DashboardService
from app.modules.referentiel.schemas import AnneeScolairePublique

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_RESTREINT = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
_ADMIN_SEUL = exige_role(RoleUtilisateur.ADMIN)


@router.get("/annees-dispo", response_model=list[AnneeScolairePublique])
async def annees_disponibles(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_RESTREINT),
) -> list[AnneeScolairePublique]:
    annees = await DashboardService(session).annees_disponibles()
    return [AnneeScolairePublique.model_validate(a) for a in annees]


@router.get("/restreint", response_model=IndicateursRestreints)
async def obtenir_indicateurs_restreints(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_RESTREINT),
) -> IndicateursRestreints:
    return await DashboardService(session).indicateurs_restreints(periode)


@router.get("/complet", response_model=IndicateursComplets)
async def obtenir_indicateurs_complets(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> IndicateursComplets:
    return await DashboardService(session).indicateurs_complets(periode)
