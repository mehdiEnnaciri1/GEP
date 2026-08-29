"""Endpoints HTTP du module paiements. Voir §6.6 de docs/01-architecture.md :
« Paiements — Complet + annulation (ADMIN) / Enregistrer (CAISSIER) / Aucun
(PROFESSEUR) » — l'annulation est réservée à ADMIN, l'encaissement est ouvert
à CAISSIER, la génération des échéances (action de fond, tous les élèves à la
fois) est réservée à ADMIN."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotence import obtenir_cle_idempotence
from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.paiements.schemas import (
    AnnulationPaiement,
    EcheanceImpayeePublique,
    EncaissementFraisInscription,
    EncaissementMensualite,
    GenerationEcheancesReponse,
    GenerationEcheancesRequete,
    PaiementPublique,
)
from app.modules.paiements.service import PaiementService

router = APIRouter(prefix="/paiements", tags=["paiements"])

_ENCAISSER = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
_ADMIN_SEUL = exige_role(RoleUtilisateur.ADMIN)


def _adresse_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/frais-inscription", response_model=PaiementPublique, status_code=201)
async def encaisser_frais_inscription(
    donnees: EncaissementFraisInscription,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ENCAISSER),
    cle_idempotence: uuid.UUID | None = Depends(obtenir_cle_idempotence),
) -> PaiementPublique:
    paiement = await PaiementService(session).encaisser_frais_inscription(
        eleve_id=donnees.eleve_id,
        montant_cents=donnees.montant_cents,
        mode=donnees.mode,
        date_paiement=donnees.date_paiement,
        cle_idempotence=cle_idempotence,
        utilisateur_id=utilisateur.id,
        adresse_ip=_adresse_ip(request),
    )
    return PaiementPublique.model_validate(paiement)


@router.post("/mensualite", response_model=PaiementPublique, status_code=201)
async def encaisser_mensualite(
    donnees: EncaissementMensualite,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ENCAISSER),
    cle_idempotence: uuid.UUID | None = Depends(obtenir_cle_idempotence),
) -> PaiementPublique:
    paiement = await PaiementService(session).encaisser_mensualite(
        eleve_id=donnees.eleve_id,
        periode=donnees.periode,
        montant_cents=donnees.montant_cents,
        mode=donnees.mode,
        date_paiement=donnees.date_paiement,
        cle_idempotence=cle_idempotence,
        utilisateur_id=utilisateur.id,
        adresse_ip=_adresse_ip(request),
    )
    return PaiementPublique.model_validate(paiement)


@router.post("/{paiement_id}/annuler", response_model=PaiementPublique)
async def annuler_paiement(
    paiement_id: int,
    donnees: AnnulationPaiement,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> PaiementPublique:
    paiement = await PaiementService(session).annuler(
        paiement_id, donnees.motif, utilisateur.id, _adresse_ip(request)
    )
    return PaiementPublique.model_validate(paiement)


@router.get("/historique/{eleve_id}", response_model=list[PaiementPublique])
async def historique_paiements(
    eleve_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ENCAISSER),
) -> list[PaiementPublique]:
    paiements = await PaiementService(session).historique_eleve(eleve_id)
    return [PaiementPublique.model_validate(p) for p in paiements]


@router.get("/impayes", response_model=list[EcheanceImpayeePublique])
async def lister_impayes(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ENCAISSER),
) -> list[EcheanceImpayeePublique]:
    echeances_et_eleves = await PaiementService(session).lister_impayes(periode)
    return [
        EcheanceImpayeePublique(
            id=echeance.id,
            eleve_id=echeance.eleve_id,
            periode=echeance.periode,
            montant_du_cents=echeance.montant_du_cents,
            montant_paye_cents=echeance.montant_paye_cents,
            statut=echeance.statut,
            eleve_nom=eleve.nom,
            eleve_prenom=eleve.prenom,
            eleve_matricule=eleve.matricule,
            eleve_niveau_code=eleve.niveau_code,
        )
        for echeance, eleve in echeances_et_eleves
    ]


@router.post("/generer-echeances", response_model=GenerationEcheancesReponse)
async def generer_echeances(
    donnees: GenerationEcheancesRequete,
    request: Request,
    session: AsyncSession = Depends(get_session),
    utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> GenerationEcheancesReponse:
    nombre = await PaiementService(session).generer_echeances(
        donnees.periode, utilisateur.id, _adresse_ip(request)
    )
    return GenerationEcheancesReponse(nombre_generees=nombre)
