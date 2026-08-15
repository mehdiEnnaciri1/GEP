"""Endpoints HTTP du module paie. Voir §6.6 de docs/01-architecture.md :
« Paie — Générer, valider (ADMIN) / Aucun (CAISSIER) / Sa paie en lecture
(PROFESSEUR) ». Le caissier n'a accès à AUCUN endpoint de ce module, pas même
en lecture (voir CLAUDE.md, §Permissions) — pas un filtrage côté client."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.paie.models import LignePaie, PaieMensuelle
from app.modules.paie.schemas import (
    AjustementPaieRequete,
    GenerationPaieReponse,
    GenerationPaieRequete,
    LignePaiePublique,
    MarquagePaye,
    PaieMensuelleDetail,
    PaieMensuellePublique,
)
from app.modules.paie.service import PaieService

router = APIRouter(prefix="/paie", tags=["paie"])

_ADMIN_SEUL = exige_role(RoleUtilisateur.ADMIN)
_PROFESSEUR = exige_role(RoleUtilisateur.PROFESSEUR)


def _adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _avec_lignes(paie: PaieMensuelle, lignes: list[LignePaie]) -> PaieMensuelleDetail:
    return PaieMensuelleDetail(
        **PaieMensuellePublique.model_validate(paie).model_dump(),
        lignes=[LignePaiePublique.model_validate(ligne) for ligne in lignes],
    )


@router.post("/generer", response_model=GenerationPaieReponse)
async def generer_paie(
    donnees: GenerationPaieRequete,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> GenerationPaieReponse:
    nombre = await PaieService(session).generer(
        donnees.periode, utilisateur.id, _adresse_ip(request)
    )
    return GenerationPaieReponse(nombre_generees=nombre)


@router.get("", response_model=list[PaieMensuellePublique])
async def lister_paies(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> list[PaieMensuellePublique]:
    paies = await PaieService(session).lister(periode)
    return [PaieMensuellePublique.model_validate(p) for p in paies]


@router.get("/mes-paies", response_model=list[PaieMensuelleDetail])
async def lister_mes_paies(
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_PROFESSEUR),
) -> list[PaieMensuelleDetail]:
    service = PaieService(session)
    paies = (
        await service.lister_par_professeur(utilisateur.professeur_id)
        if utilisateur.professeur_id is not None
        else []
    )
    resultat = []
    for paie in paies:
        _, lignes = await service.obtenir_detail(paie.id)
        resultat.append(_avec_lignes(paie, lignes))
    return resultat


@router.get("/{paie_id}", response_model=PaieMensuelleDetail)
async def obtenir_paie(
    paie_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> PaieMensuelleDetail:
    paie, lignes = await PaieService(session).obtenir_detail(paie_id)
    return _avec_lignes(paie, lignes)


@router.post("/{paie_id}/valider", response_model=PaieMensuellePublique)
async def valider_paie(
    paie_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> PaieMensuellePublique:
    paie = await PaieService(session).valider(paie_id, utilisateur.id, _adresse_ip(request))
    return PaieMensuellePublique.model_validate(paie)


@router.post("/{paie_id}/marquer-payee", response_model=PaieMensuellePublique)
async def marquer_paie_payee(
    paie_id: int,
    donnees: MarquagePaye,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> PaieMensuellePublique:
    paie = await PaieService(session).marquer_payee(
        paie_id,
        donnees.date_paiement,
        donnees.mode_paiement,
        utilisateur.id,
        _adresse_ip(request),
    )
    return PaieMensuellePublique.model_validate(paie)


@router.post("/ajustement", response_model=LignePaiePublique, status_code=201)
async def ajouter_ligne_ajustement(
    donnees: AjustementPaieRequete,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> LignePaiePublique:
    ligne = await PaieService(session).ajouter_ligne_ajustement(
        donnees, utilisateur.id, _adresse_ip(request)
    )
    return LignePaiePublique.model_validate(ligne)
