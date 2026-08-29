"""Schémas Pydantic — entrée et sortie du module eleves."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.eleves.models import ModeFacturation, StatutEleve, StatutFrais


class EleveCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = Field(min_length=1, max_length=80)
    telephone_eleve: str | None = Field(default=None, max_length=20)
    telephone_parent: str = Field(min_length=1, max_length=20)
    niveau_code: str
    date_inscription: date
    observation: str | None = None
    # NORMAL (par défaut) : matiere_ids obligatoire, au moins une matière.
    # PACK : matiere_ids ignoré — composé automatiquement de toutes les
    # matières tarifées du niveau (voir EleveService.creer).
    # PERSONNALISE : matiere_ids obligatoire comme NORMAL, mais le montant dû
    # mensuel vient de `montant_personnalise_cents`, pas de la somme des tarifs.
    mode_facturation: ModeFacturation = ModeFacturation.NORMAL
    montant_personnalise_cents: int | None = Field(default=None, ge=0)
    matiere_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _verifier_coherence_facturation(self) -> EleveCreation:
        if self.mode_facturation == ModeFacturation.PERSONNALISE:
            if self.montant_personnalise_cents is None:
                raise ValueError(
                    "montant_personnalise_cents est requis en mode de facturation PERSONNALISE."
                )
        elif self.montant_personnalise_cents is not None:
            raise ValueError(
                "montant_personnalise_cents ne s'applique qu'au mode de facturation PERSONNALISE."
            )

        if self.mode_facturation != ModeFacturation.PACK and not self.matiere_ids:
            raise ValueError("Choisissez au moins une matière.")

        return self


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
    mode_facturation: ModeFacturation
    montant_mensuel_fixe_cents: int | None
    observation: str | None


class EleveDetail(ElevePublique):
    inscriptions: list[InscriptionMatierePublique]
    frais_inscription: FraisInscriptionPublique


class PageEleves(BaseModel):
    elements: list[ElevePublique]
    total: int
    page: int
    taille: int
