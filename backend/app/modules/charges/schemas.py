"""Schémas Pydantic — entrée et sortie du module charges."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.paiements.models import ModePaiement


class CategorieChargeCreation(BaseModel):
    libelle: str = Field(min_length=1, max_length=80)


class CategorieChargeMiseAJour(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=80)
    actif: bool | None = None


class CategorieChargePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libelle: str
    actif: bool


class ChargePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categorie_id: int
    description: str
    montant_cents: int
    date_charge: date
    periode: str
    mode_paiement: ModePaiement
    justificatif_type: str | None
    cree_le: datetime
    annule_le: datetime | None


class TotalCategorie(BaseModel):
    categorie_id: int
    total_cents: int


class TotauxCharges(BaseModel):
    periode: str
    total_cents: int
    par_categorie: list[TotalCategorie]
