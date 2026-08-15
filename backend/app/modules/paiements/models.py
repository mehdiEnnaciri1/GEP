"""Paiements et échéances — voir docs/02-modele-donnees.md §4.

Un `paiement` n'est jamais modifié ni supprimé (voir CLAUDE.md). Correction =
annulation (`annule_le`, `annule_par`, `motif_annulation`) puis nouvelle
saisie. Le service recalcule alors le statut de l'échéance concernée à partir
de la formule du §8.2, jamais par transition ad hoc — c'est l'endroit où les
bugs se logent si on procède par petites incrémentations.
"""

from __future__ import annotations

import enum
import uuid
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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StatutEcheance(enum.StrEnum):
    NON_PAYE = "NON_PAYE"
    PARTIEL = "PARTIEL"
    PAYE = "PAYE"


class ModePaiement(enum.StrEnum):
    ESPECES = "ESPECES"
    VIREMENT = "VIREMENT"
    CHEQUE = "CHEQUE"
    CARTE = "CARTE"
    AUTRE = "AUTRE"


class TypePaiement(enum.StrEnum):
    MENSUALITE = "MENSUALITE"
    INSCRIPTION = "INSCRIPTION"


class Echeance(Base):
    __tablename__ = "echeance"
    __table_args__ = (
        UniqueConstraint("eleve_id", "periode", name="ux_echeance"),
        CheckConstraint(r"periode ~ '^\d{4}-(0[1-9]|1[0-2])$'", name="ck_periode_format"),
        CheckConstraint(
            "montant_du_cents >= 0 AND montant_paye_cents >= 0", name="ck_echeance_montants"
        ),
        Index(
            "ix_echeance_impayes",
            "periode",
            "statut",
            postgresql_where=text("statut <> 'PAYE'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    eleve_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("eleve.id"))
    periode: Mapped[str] = mapped_column(String(7))
    montant_du_cents: Mapped[int] = mapped_column(BigInteger)
    montant_paye_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    statut: Mapped[StatutEcheance] = mapped_column(
        Enum(StatutEcheance, name="statut_echeance"), default=StatutEcheance.NON_PAYE
    )
    genere_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LigneEcheance(Base):
    __tablename__ = "ligne_echeance"
    __table_args__ = (UniqueConstraint("echeance_id", "matiere_id", name="ux_ligne_echeance"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    echeance_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("echeance.id", ondelete="CASCADE")
    )
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    tarif_cents: Mapped[int] = mapped_column(BigInteger)


class Paiement(Base):
    __tablename__ = "paiement"
    __table_args__ = (
        CheckConstraint("montant_cents > 0", name="ck_paiement_positif"),
        CheckConstraint(
            "(type = 'MENSUALITE' AND periode IS NOT NULL) "
            "OR (type = 'INSCRIPTION' AND periode IS NULL)",
            name="ck_paiement_periode",
        ),
        CheckConstraint(
            "(annule_le IS NULL AND annule_par IS NULL AND motif_annulation IS NULL) "
            "OR (annule_le IS NOT NULL AND annule_par IS NOT NULL "
            "AND motif_annulation IS NOT NULL)",
            name="ck_annulation",
        ),
        Index("ix_paiement_eleve", "eleve_id", "date_paiement"),
        Index("ix_paiement_periode", "periode", postgresql_where=text("annule_le IS NULL")),
        Index("ix_paiement_date", "date_paiement", postgresql_where=text("annule_le IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    numero_recu: Mapped[str] = mapped_column(String(20), unique=True)
    eleve_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("eleve.id"))
    type: Mapped[TypePaiement] = mapped_column(Enum(TypePaiement, name="type_paiement"))
    periode: Mapped[str | None] = mapped_column(String(7), nullable=True)
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    date_paiement: Mapped[date] = mapped_column(Date)
    mode: Mapped[ModePaiement] = mapped_column(Enum(ModePaiement, name="mode_paiement"))
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Annulation — voir CLAUDE.md : jamais de modification ni de suppression.
    annule_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    annule_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("utilisateur.id"), nullable=True
    )
    motif_annulation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Traçabilité
    cree_par: Mapped[int] = mapped_column(BigInteger, ForeignKey("utilisateur.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cle_idempotence: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=True
    )


__all__ = [
    "Echeance",
    "StatutEcheance",
    "LigneEcheance",
    "Paiement",
    "ModePaiement",
    "TypePaiement",
]
