"""Endpoints HTTP du module charges. Voir §6.6 de docs/01-architecture.md :
« Charges — Complet (ADMIN) / Aucun (CAISSIER) / Aucun (PROFESSEUR) » — ni le
caissier ni le professeur n'ont accès à un seul endpoint de ce module, pas
même en lecture."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.charges.schemas import (
    CategorieChargeCreation,
    CategorieChargeMiseAJour,
    CategorieChargePublique,
    ChargePublique,
    EvolutionChargesReponse,
    TotalCategorie,
    TotauxCharges,
)
from app.modules.charges.service import CategorieChargeService, ChargeService
from app.modules.paiements.models import ModePaiement

router = APIRouter(prefix="/charges", tags=["charges"])

_ADMIN_SEUL = exige_role(RoleUtilisateur.ADMIN)


def _adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---- Catégories --------------------------------------------------------------


@router.get("/categories", response_model=list[CategorieChargePublique])
async def lister_categories(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> list[CategorieChargePublique]:
    categories = await CategorieChargeService(session).lister()
    return [CategorieChargePublique.model_validate(c) for c in categories]


@router.post("/categories", response_model=CategorieChargePublique, status_code=201)
async def creer_categorie(
    donnees: CategorieChargeCreation,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> CategorieChargePublique:
    categorie = await CategorieChargeService(session).creer(donnees)
    return CategorieChargePublique.model_validate(categorie)


@router.patch("/categories/{categorie_id}", response_model=CategorieChargePublique)
async def mettre_a_jour_categorie(
    categorie_id: int,
    donnees: CategorieChargeMiseAJour,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> CategorieChargePublique:
    categorie = await CategorieChargeService(session).mettre_a_jour(categorie_id, donnees)
    return CategorieChargePublique.model_validate(categorie)


# ---- Totaux (§8.3 : total mensuel, total par catégorie) -----------------------


@router.get("/totaux", response_model=TotauxCharges)
async def obtenir_totaux(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> TotauxCharges:
    total, par_categorie = await ChargeService(session).totaux(periode)
    return TotauxCharges(
        periode=periode,
        total_cents=total,
        par_categorie=[
            TotalCategorie(categorie_id=categorie_id, total_cents=total_cents)
            for categorie_id, total_cents in par_categorie
        ],
    )


@router.get("/evolution-mensuelle", response_model=EvolutionChargesReponse)
async def obtenir_evolution_mensuelle(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> EvolutionChargesReponse:
    return await ChargeService(session).evolution_mensuelle()


# ---- Charges -------------------------------------------------------------------


@router.get("", response_model=list[ChargePublique])
async def lister_charges(
    periode: str | None = None,
    categorie_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> list[ChargePublique]:
    charges = await ChargeService(session).lister(periode=periode, categorie_id=categorie_id)
    return [ChargePublique.model_validate(c) for c in charges]


@router.post("", response_model=ChargePublique, status_code=201)
async def creer_charge(
    request: Request,
    categorie_id: int = Form(...),
    description: str = Form(...),
    montant_cents: int = Form(..., gt=0),
    date_charge: date = Form(...),
    periode: str = Form(..., min_length=7, max_length=7),
    mode_paiement: ModePaiement = Form(...),
    justificatif: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> ChargePublique:
    contenu = await justificatif.read() if justificatif is not None else None
    charge = await ChargeService(session).creer(
        categorie_id=categorie_id,
        description=description,
        montant_cents=montant_cents,
        date_charge=date_charge,
        periode=periode,
        mode_paiement=mode_paiement,
        justificatif=contenu,
        utilisateur_id=utilisateur.id,
        adresse_ip=_adresse_ip(request),
    )
    return ChargePublique.model_validate(charge)


@router.get("/{charge_id}", response_model=ChargePublique)
async def obtenir_charge(
    charge_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> ChargePublique:
    charge = await ChargeService(session).obtenir(charge_id)
    return ChargePublique.model_validate(charge)


@router.get("/{charge_id}/justificatif")
async def obtenir_justificatif(
    charge_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> Response:
    contenu, type_mime = await ChargeService(session).obtenir_justificatif(charge_id)
    return Response(content=contenu, media_type=type_mime)


@router.post("/{charge_id}/annuler", response_model=ChargePublique)
async def annuler_charge(
    charge_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> ChargePublique:
    charge = await ChargeService(session).annuler(charge_id, utilisateur.id, _adresse_ip(request))
    return ChargePublique.model_validate(charge)
