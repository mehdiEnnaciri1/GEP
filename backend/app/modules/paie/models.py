"""Paie mensuelle des professeurs — voir docs/02-modele-donnees.md §5.

Une `paie_mensuelle` en statut `VALIDEE` ou `PAYEE` est verrouillée (voir
CLAUDE.md) : toute correction passe par une ligne d'ajustement sur la période
SUIVANTE, jamais par une modification des lignes déjà générées.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.paiements.models import ModePaiement


class StatutPaie(enum.StrEnum):
    BROUILLON = "BROUILLON"
    VALIDEE = "VALIDEE"
    PAYEE = "PAYEE"


class PaieMensuelle(Base):
    __tablename__ = "paie_mensuelle"
    __table_args__ = (
        UniqueConstraint("professeur_id", "periode", name="ux_paie"),
        CheckConstraint("total_cents >= 0", name="ck_paie_total"),
        CheckConstraint(r"periode ~ '^\d{4}-(0[1-9]|1[0-2])$'", name="ck_paie_periode_format"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    professeur_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("professeur.id"))
    periode: Mapped[str] = mapped_column(String(7))
    total_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    statut: Mapped[StatutPaie] = mapped_column(
        Enum(StatutPaie, name="statut_paie"), default=StatutPaie.BROUILLON
    )
    genere_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    validee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validee_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("utilisateur.id"), nullable=True
    )
    payee_le: Mapped[date | None] = mapped_column(Date, nullable=True)
    mode_paiement: Mapped[ModePaiement | None] = mapped_column(
        Enum(ModePaiement, name="mode_paiement"), nullable=True
    )


class LignePaie(Base):
    __tablename__ = "ligne_paie"
    __table_args__ = (
        UniqueConstraint(
            "paie_id", "matiere_id", "niveau_code", "est_ajustement", name="ux_ligne_paie"
        ),
        CheckConstraint(
            "est_ajustement OR montant_cents = nombre_eleves * tarif_unitaire_cents",
            name="ck_ligne_paie_calcul",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    paie_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("paie_mensuelle.id", ondelete="CASCADE")
    )
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    nombre_eleves: Mapped[int] = mapped_column(Integer)
    # ⚠ FIGÉ à la génération (décision D1, même principe que
    # inscription_matiere.tarif_mensuel_cents) : modifier tarif_professeur
    # ensuite ne doit rien changer aux paies déjà générées.
    tarif_unitaire_cents: Mapped[int] = mapped_column(BigInteger)
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    est_ajustement: Mapped[bool] = mapped_column(Boolean, default=False)
    motif_ajustement: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["StatutPaie", "PaieMensuelle", "LignePaie"]
