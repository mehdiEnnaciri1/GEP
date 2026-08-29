"""Endpoints HTTP du module eleves. ADMIN et CAISSIER ont accès complet
(création, modification, changement de statut) — voir §6.6 de
docs/01-architecture.md. PROFESSEUR n'a encore accès à rien ici : la lecture
« de ses niveaux » dépend des affectations (étape 5), pas encore construites ;
en attendant, refuser plutôt que d'exposer tous les élèves par erreur."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RessourceIntrouvable
from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.eleves.models import Eleve, FraisInscription, InscriptionMatiere, StatutEleve
from app.modules.eleves.schemas import (
    ChangementStatut,
    DefinirPack,
    DefinirReduction,
    EleveCreation,
    EleveDetail,
    EleveMiseAJour,
    ElevePublique,
    FraisInscriptionPublique,
    InscriptionMatierePublique,
    PageEleves,
)
from app.modules.eleves.service import EleveService

router = APIRouter(prefix="/eleves", tags=["eleves"])

_ACCES = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)


def _adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _detail(
    eleve: Eleve, inscriptions: list[InscriptionMatiere], frais: FraisInscription | None
) -> EleveDetail:
    if frais is None:  # pragma: no cover — toujours créé à la création de l'élève
        raise RessourceIntrouvable("Frais d'inscription introuvable.")
    return EleveDetail(
        **ElevePublique.model_validate(eleve).model_dump(),
        inscriptions=[InscriptionMatierePublique.model_validate(i) for i in inscriptions],
        frais_inscription=FraisInscriptionPublique.model_validate(frais),
    )


@router.get("", response_model=PageEleves)
async def lister_eleves(
    recherche: str | None = None,
    niveau_code: str | None = None,
    statut: StatutEleve | None = None,
    page: int = Query(default=1, ge=1),
    taille: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ACCES),
) -> PageEleves:
    elements, total = await EleveService(session).lister(
        recherche=recherche, niveau_code=niveau_code, statut=statut, page=page, taille=taille
    )
    return PageEleves(
        elements=[ElevePublique.model_validate(e) for e in elements],
        total=total,
        page=page,
        taille=taille,
    )


@router.post("", response_model=EleveDetail, status_code=201)
async def creer_eleve(
    donnees: EleveCreation,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ACCES),
) -> EleveDetail:
    eleve, inscriptions, frais = await EleveService(session).creer(
        donnees, utilisateur.id, _adresse_ip(request)
    )
    return _detail(eleve, inscriptions, frais)


@router.get("/{eleve_id}", response_model=EleveDetail)
async def obtenir_eleve(
    eleve_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ACCES),
) -> EleveDetail:
    eleve, inscriptions, frais = await EleveService(session).obtenir_detail(eleve_id)
    return _detail(eleve, inscriptions, frais)


@router.patch("/{eleve_id}", response_model=ElevePublique)
async def mettre_a_jour_eleve(
    eleve_id: int,
    donnees: EleveMiseAJour,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ACCES),
) -> ElevePublique:
    eleve = await EleveService(session).mettre_a_jour(
        eleve_id, donnees, utilisateur.id, _adresse_ip(request)
    )
    return ElevePublique.model_validate(eleve)


@router.post("/{eleve_id}/statut", response_model=ElevePublique)
async def changer_statut_eleve(
    eleve_id: int,
    donnees: ChangementStatut,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ACCES),
) -> ElevePublique:
    eleve = await EleveService(session).changer_statut(
        eleve_id, donnees.statut, utilisateur.id, _adresse_ip(request)
    )
    return ElevePublique.model_validate(eleve)


@router.post("/{eleve_id}/pack", response_model=EleveDetail)
async def definir_pack_eleve(
    eleve_id: int,
    donnees: DefinirPack,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ACCES),
) -> EleveDetail:
    eleve, inscriptions, frais = await EleveService(session).definir_pack(
        eleve_id, donnees, utilisateur.id, _adresse_ip(request)
    )
    return _detail(eleve, inscriptions, frais)


@router.post("/{eleve_id}/reduction", response_model=ElevePublique)
async def definir_reduction_eleve(
    eleve_id: int,
    donnees: DefinirReduction,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ACCES),
) -> ElevePublique:
    eleve = await EleveService(session).definir_reduction(
        eleve_id, donnees, utilisateur.id, _adresse_ip(request)
    )
    return ElevePublique.model_validate(eleve)
