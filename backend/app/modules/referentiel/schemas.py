"""Schémas Pydantic — entrée et sortie du module referentiel."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AnneeScolaireCreation(BaseModel):
    libelle: str = Field(min_length=9, max_length=9, examples=["2025-2026"])
    date_debut: date
    date_fin: date


class AnneeScolaireMiseAJour(BaseModel):
    libelle: str | None = Field(default=None, min_length=9, max_length=9)
    date_debut: date | None = None
    date_fin: date | None = None


class AnneeScolairePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libelle: str
    date_debut: date
    date_fin: date
    est_active: bool


class NiveauPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    libelle: str
    ordre: int


class MatiereCreation(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    libelle: str = Field(min_length=1, max_length=80)


class MatiereMiseAJour(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=80)
    actif: bool | None = None


class MatierePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    libelle: str
    actif: bool


class ParametrePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cle: str
    valeur: str
    type_valeur: str
    description: str | None


class ParametreMiseAJour(BaseModel):
    valeur: str


class TarifEleveDefinition(BaseModel):
    annee_scolaire_id: int
    niveau_code: str
    matiere_id: int
    montant_cents: int = Field(ge=0)


class TarifElevePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee_scolaire_id: int
    niveau_code: str
    matiere_id: int
    montant_cents: int


class TarifPackDefinition(BaseModel):
    annee_scolaire_id: int
    niveau_code: str
    montant_cents: int = Field(ge=0)


class TarifPackPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee_scolaire_id: int
    niveau_code: str
    montant_cents: int


class TarifProfesseurDefinition(BaseModel):
    annee_scolaire_id: int
    niveau_code: str
    matiere_id: int
    montant_par_eleve_cents: int = Field(ge=0)


class TarifProfesseurPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee_scolaire_id: int
    niveau_code: str
    matiere_id: int
    montant_par_eleve_cents: int
