"""Endpoints HTTP du module professeurs. Voir §6.6 de docs/01-architecture.md :
« Professeurs — Complet (ADMIN) / Lecture (CAISSIER) / Sa fiche (PROFESSEUR) ».
`/professeurs/me` sert la fiche du professeur connecté — un endpoint séparé,
pas un filtrage côté client (même principe que pour le bénéfice net et le
caissier, voir §6.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RessourceIntrouvable
from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.professeurs.models import Affectation, Professeur
from app.modules.professeurs.schemas import (
    AffectationCreation,
    AffectationPublique,
    ProfesseurCreation,
    ProfesseurDetail,
    ProfesseurMiseAJour,
    ProfesseurPublique,
)
from app.modules.professeurs.service import AffectationService, ProfesseurService

router = APIRouter(tags=["professeurs"])

_LECTURE = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
_ECRITURE = exige_role(RoleUtilisateur.ADMIN)
_PROFESSEUR = exige_role(RoleUtilisateur.PROFESSEUR)


def _affectation_publique(affectation: Affectation, nombre_eleves: int) -> AffectationPublique:
    return AffectationPublique(
        id=affectation.id,
        professeur_id=affectation.professeur_id,
        matiere_id=affectation.matiere_id,
        niveau_code=affectation.niveau_code,
        annee_scolaire_id=affectation.annee_scolaire_id,
        date_debut=affectation.date_debut,
        date_fin=affectation.date_fin,
        nombre_eleves=nombre_eleves,
    )


def _detail(
    professeur: Professeur, affectations_avec_compteur: list[tuple[Affectation, int]]
) -> ProfesseurDetail:
    return ProfesseurDetail(
        **ProfesseurPublique.model_validate(professeur).model_dump(),
        affectations=[
            _affectation_publique(affectation, nombre_eleves)
            for affectation, nombre_eleves in affectations_avec_compteur
        ],
    )


# ---- Professeurs ------------------------------------------------------------


@router.get("/professeurs", response_model=list[ProfesseurPublique])
async def lister_professeurs(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[ProfesseurPublique]:
    professeurs = await ProfesseurService(session).lister()
    return [ProfesseurPublique.model_validate(p) for p in professeurs]


@router.post("/professeurs", response_model=ProfesseurPublique, status_code=201)
async def creer_professeur(
    donnees: ProfesseurCreation,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> ProfesseurPublique:
    professeur = await ProfesseurService(session).creer(donnees)
    return ProfesseurPublique.model_validate(professeur)


@router.get("/professeurs/me", response_model=ProfesseurDetail)
async def obtenir_ma_fiche(
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_PROFESSEUR),
) -> ProfesseurDetail:
    if utilisateur.professeur_id is None:  # pragma: no cover — garanti par ck_prof_lie
        raise RessourceIntrouvable("Aucune fiche professeur associée à ce compte.")
    professeur, affectations = await ProfesseurService(session).obtenir_detail(
        utilisateur.professeur_id
    )
    return _detail(professeur, affectations)


@router.patch("/professeurs/{professeur_id}", response_model=ProfesseurPublique)
async def mettre_a_jour_professeur(
    professeur_id: int,
    donnees: ProfesseurMiseAJour,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> ProfesseurPublique:
    professeur = await ProfesseurService(session).mettre_a_jour(professeur_id, donnees)
    return ProfesseurPublique.model_validate(professeur)


@router.get("/professeurs/{professeur_id}", response_model=ProfesseurDetail)
async def obtenir_professeur(
    professeur_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> ProfesseurDetail:
    professeur, affectations = await ProfesseurService(session).obtenir_detail(professeur_id)
    return _detail(professeur, affectations)


# ---- Affectations -------------------------------------------------------------


@router.get("/affectations", response_model=list[AffectationPublique])
async def lister_affectations(
    annee_scolaire_id: int | None = None,
    professeur_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[AffectationPublique]:
    affectations = await AffectationService(session).lister(
        annee_scolaire_id=annee_scolaire_id, professeur_id=professeur_id
    )
    return [
        _affectation_publique(affectation, nombre_eleves)
        for affectation, nombre_eleves in affectations
    ]


@router.post("/affectations", response_model=AffectationPublique, status_code=201)
async def creer_affectation(
    donnees: AffectationCreation,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> AffectationPublique:
    affectation = await AffectationService(session).creer(donnees)
    return _affectation_publique(affectation, nombre_eleves=0)


@router.delete("/affectations/{affectation_id}", status_code=204)
async def supprimer_affectation(
    affectation_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> None:
    await AffectationService(session).supprimer(affectation_id)
