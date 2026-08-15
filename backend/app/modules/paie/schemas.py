"""Schémas Pydantic — entrée et sortie du module paie."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.paie.models import StatutPaie
from app.modules.paiements.models import ModePaiement


class GenerationPaieRequete(BaseModel):
    periode: str = Field(min_length=7, max_length=7)


class GenerationPaieReponse(BaseModel):
    nombre_generees: int


class MarquagePaye(BaseModel):
    date_paiement: date
    mode_paiement: ModePaiement


class AjustementPaieRequete(BaseModel):
    professeur_id: int
    periode: str = Field(min_length=7, max_length=7)
    matiere_id: int
    niveau_code: str
    montant_cents: int
    motif: str = Field(min_length=1)


class LignePaiePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matiere_id: int
    niveau_code: str
    nombre_eleves: int
    tarif_unitaire_cents: int
    montant_cents: int
    est_ajustement: bool
    motif_ajustement: str | None


class PaieMensuellePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    professeur_id: int
    periode: str
    total_cents: int
    statut: StatutPaie
    validee_le: datetime | None
    payee_le: date | None
    mode_paiement: ModePaiement | None


class PaieMensuelleDetail(PaieMensuellePublique):
    lignes: list[LignePaiePublique]
