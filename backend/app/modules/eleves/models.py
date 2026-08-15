"""Élèves et inscriptions — voir docs/02-modele-donnees.md §3."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StatutEleve(enum.StrEnum):
    ACTIF = "ACTIF"
    SUSPENDU = "SUSPENDU"
    ARCHIVE = "ARCHIVE"


class Eleve(Base):
    __tablename__ = "eleve"
    __table_args__ = (
        Index(
            "ix_eleve_niveau_annee",
            "annee_scolaire_id",
            "niveau_code",
            postgresql_where=text("statut = 'ACTIF'"),
        ),
        Index("ix_eleve_nom", "nom", "prenom"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    matricule: Mapped[str] = mapped_column(String(20), unique=True)
    nom: Mapped[str] = mapped_column(String(80))
    prenom: Mapped[str] = mapped_column(String(80))
    telephone_eleve: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telephone_parent: Mapped[str] = mapped_column(String(20))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    annee_scolaire_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("annee_scolaire.id"))
    date_inscription: Mapped[date] = mapped_column(Date)
    statut: Mapped[StatutEleve] = mapped_column(
        Enum(StatutEleve, name="statut_eleve"), default=StatutEleve.ACTIF
    )
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    cree_par: Mapped[int] = mapped_column(BigInteger, ForeignKey("utilisateur.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InscriptionMatiere(Base):
    __tablename__ = "inscription_matiere"
    __table_args__ = (
        CheckConstraint("date_fin IS NULL OR date_fin >= date_debut", name="ck_insc_dates"),
        CheckConstraint("tarif_mensuel_cents >= 0", name="ck_insc_tarif"),
        # Un élève ne peut avoir qu'une inscription EN COURS par matière.
        Index(
            "ux_inscription_active",
            "eleve_id",
            "matiere_id",
            unique=True,
            postgresql_where=text("date_fin IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    eleve_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("eleve.id"))
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    # ⚠ COPIE de tarif_eleve au moment de l'inscription, jamais une référence
    # (décision D1) : modifier le référentiel plus tard ne doit rien changer ici.
    tarif_mensuel_cents: Mapped[int] = mapped_column(BigInteger)
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    cree_par: Mapped[int] = mapped_column(BigInteger, ForeignKey("utilisateur.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StatutFrais(enum.StrEnum):
    NON_PAYE = "NON_PAYE"
    PAYE = "PAYE"


class FraisInscription(Base):
    __tablename__ = "frais_inscription"
    __table_args__ = (
        CheckConstraint(
            "(statut = 'PAYE' AND date_paiement IS NOT NULL AND paiement_id IS NOT NULL) "
            "OR (statut = 'NON_PAYE' AND date_paiement IS NULL)",
            name="ck_frais_coherent",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    eleve_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("eleve.id"), unique=True)
    # Copie du paramètre frais_inscription_cents au moment de la création de l'élève.
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    statut: Mapped[StatutFrais] = mapped_column(
        Enum(StatutFrais, name="statut_frais"), default=StatutFrais.NON_PAYE
    )
    date_paiement: Mapped[date | None] = mapped_column(Date, nullable=True)
    mode_paiement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # ⚠ La table `paiement` n'existe pas encore (étape 4). Colonne nullable,
    # sans ForeignKey pour l'instant ; la FK sera ajoutée dans une migration
    # ultérieure quand `paiement` sera créée.
    paiement_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "Eleve",
    "StatutEleve",
    "InscriptionMatiere",
    "FraisInscription",
    "StatutFrais",
]
