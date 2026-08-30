"""Schémas Pydantic — entrée et sortie du module eleves."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.eleves.models import StatutEleve, StatutFrais


class EleveCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=80)
    prenom: str = Field(min_length=1, max_length=80)
    telephone_eleve: str | None = Field(default=None, max_length=20)
    telephone_parent: str = Field(min_length=1, max_length=20)
    niveau_code: str
    date_inscription: date
    observation: str | None = None
    # est_pack=True : matiere_ids ignoré — composé automatiquement de toutes
    # les matières tarifées du niveau (voir EleveService.creer). Sinon,
    # matiere_ids est obligatoire, y compris avec une réduction : les
    # matières suivies restent réelles, seule l'échéance les ignore.
    est_pack: bool = False
    reduction_mensuelle_cents: int | None = Field(default=None, ge=0)
    matiere_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _verifier_coherence_facturation(self) -> EleveCreation:
        if self.est_pack and self.reduction_mensuelle_cents is not None:
            raise ValueError("Pack et réduction ne peuvent pas être actifs en même temps.")
        if not self.est_pack and not self.matiere_ids:
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


class ModifierEngagement(BaseModel):
    """Remplace la configuration de facturation d'un élève (matières, pack ou
    réduction) à partir du mois choisi (`periode_application`, format
    YYYY-MM) — jamais rétroactif sur un mois dont l'échéance est déjà
    générée (voir EleveService.modifier_engagement). Mêmes règles de
    cohérence qu'à la création (voir EleveCreation)."""

    periode_application: str
    est_pack: bool = False
    reduction_mensuelle_cents: int | None = Field(default=None, ge=0)
    matiere_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _verifier_coherence_facturation(self) -> ModifierEngagement:
        if self.est_pack and self.reduction_mensuelle_cents is not None:
            raise ValueError("Pack et réduction ne peuvent pas être actifs en même temps.")
        if not self.est_pack and not self.matiere_ids:
            raise ValueError("Choisissez au moins une matière.")
        return self


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
    est_pack: bool
    reduction_mensuelle_cents: int | None
    observation: str | None


class EleveDetail(ElevePublique):
    inscriptions: list[InscriptionMatierePublique]
    frais_inscription: FraisInscriptionPublique


class PageEleves(BaseModel):
    elements: list[ElevePublique]
    total: int
    page: int
    taille: int
