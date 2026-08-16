"""Charges du centre — voir docs/02-modele-donnees.md §6.

`date_charge` et `periode` sont distincts volontairement : une facture
d'électricité payée le 5 novembre peut concerner le mois d'octobre. Le
dashboard raisonne sur `periode`, la trésorerie sur `date_charge`.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from app.modules.paiements.models import ModePaiement


class CategorieCharge(Base):
    __tablename__ = "categorie_charge"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    libelle: Mapped[str] = mapped_column(String(80), unique=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Charge(Base):
    __tablename__ = "charge"
    __table_args__ = (
        CheckConstraint("montant_cents > 0", name="ck_charge_positive"),
        CheckConstraint(r"periode ~ '^\d{4}-(0[1-9]|1[0-2])$'", name="ck_charge_periode"),
        Index("ix_charge_periode", "periode", postgresql_where=text("annule_le IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    categorie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categorie_charge.id"))
    description: Mapped[str] = mapped_column(Text)
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    date_charge: Mapped[date] = mapped_column(Date)
    periode: Mapped[str] = mapped_column(String(7))
    mode_paiement: Mapped[ModePaiement] = mapped_column(Enum(ModePaiement, name="mode_paiement"))
    # Chemin relatif sous reglages.chemin_justificatifs, jamais le binaire en
    # base (voir app/shared/stockage.py) ; type MIME détecté sur les octets
    # réels du fichier, pas sur l'extension déclarée par le client.
    justificatif_chemin: Mapped[str | None] = mapped_column(Text, nullable=True)
    justificatif_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cree_par: Mapped[int] = mapped_column(BigInteger, ForeignKey("utilisateur.id"))
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Pas de suppression ni de modification d'une charge enregistrée — même
    # principe que paiement/paie_mensuelle : correction = annulation.
    annule_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["CategorieCharge", "Charge"]
