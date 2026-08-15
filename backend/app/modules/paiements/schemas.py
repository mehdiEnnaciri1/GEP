"""Schémas Pydantic — entrée et sortie du module paiements."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.paiements.models import ModePaiement, StatutEcheance


class EncaissementFraisInscription(BaseModel):
    eleve_id: int
    montant_cents: int = Field(gt=0)
    mode: ModePaiement
    date_paiement: date


class EncaissementMensualite(BaseModel):
    eleve_id: int
    periode: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    montant_cents: int = Field(gt=0)
    mode: ModePaiement
    date_paiement: date


class AnnulationPaiement(BaseModel):
    motif: str = Field(min_length=1)


class PaiementPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_recu: str
    eleve_id: int
    type: str
    periode: str | None
    montant_cents: int
    date_paiement: date
    mode: ModePaiement
    observation: str | None
    annule_le: datetime | None
    motif_annulation: str | None


class EcheancePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eleve_id: int
    periode: str
    montant_du_cents: int
    montant_paye_cents: int
    statut: StatutEcheance


class EcheanceImpayeePublique(EcheancePublique):
    """Étend EcheancePublique avec de quoi identifier l'élève à l'écran —
    afficher un simple ID sur un tableau d'impayés n'est pas exploitable."""

    eleve_nom: str
    eleve_prenom: str
    eleve_matricule: str


class GenerationEcheancesRequete(BaseModel):
    periode: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class GenerationEcheancesReponse(BaseModel):
    nombre_generees: int
