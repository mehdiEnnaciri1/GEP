"""Schémas Pydantic — entrée et sortie du module professeurs."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ProfesseurCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = Field(min_length=1, max_length=80)
    telephone: str = Field(min_length=1, max_length=20)


class ProfesseurMiseAJour(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=80)
    prenom: str | None = Field(default=None, min_length=1, max_length=80)
    telephone: str | None = Field(default=None, min_length=1, max_length=20)
    actif: bool | None = None


class ProfesseurPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    actif: bool


class AffectationCreation(BaseModel):
    professeur_id: int
    matiere_id: int
    niveau_code: str
    annee_scolaire_id: int
    date_debut: date
    date_fin: date | None = None


class AffectationPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    professeur_id: int
    matiere_id: int
    niveau_code: str
    annee_scolaire_id: int
    date_debut: date
    date_fin: date | None
    nombre_eleves: int


class ProfesseurDetail(ProfesseurPublique):
    affectations: list[AffectationPublique]
