"""Schémas Pydantic — entrée et sortie du module eleves."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.modules.eleves.models import StatutEleve, StatutFrais


class EleveCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = Field(min_length=1, max_length=80)
    telephone_eleve: str | None = Field(default=None, max_length=20)
    telephone_parent: str = Field(min_length=1, max_length=20)
    niveau_code: str
    date_inscription: date
    observation: str | None = None
    matiere_ids: list[int] = Field(min_length=1)


class EleveMiseAJour(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=80)
    prenom: str | None = Field(default=None, min_length=1, max_length=80)
    telephone_eleve: str | None = Field(default=None, max_length=20)
    telephone_parent: str | None = Field(default=None, min_length=1, max_length=20)
    observation: str | None = None


class ChangementStatut(BaseModel):
    statut: StatutEleve


class InscriptionMatierePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matiere_id: int
    tarif_mensuel_cents: int
    date_debut: date
    date_fin: date | None


class FraisInscriptionPublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    montant_cents: int
    statut: StatutFrais
    date_paiement: date | None
    mode_paiement: str | None


class ElevePublique(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricule: str
    nom: str
    prenom: str
    telephone_eleve: str | None
    telephone_parent: str
    niveau_code: str
    annee_scolaire_id: int
    date_inscription: date
    statut: StatutEleve
    observation: str | None


class EleveDetail(ElevePublique):
    inscriptions: list[InscriptionMatierePublique]
    frais_inscription: FraisInscriptionPublique


class PageEleves(BaseModel):
    elements: list[ElevePublique]
    total: int
    page: int
    taille: int
