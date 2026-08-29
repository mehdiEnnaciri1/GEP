"""Référentiel — voir docs/02-modele-donnees.md §1.

`tarif_eleve` et `tarif_professeur` restent deux tables distinctes,
volontairement : unités différentes (forfait mensuel contre montant par
élève), propriétaires fonctionnels différents, rythmes de révision
différents. Ne pas les fusionner (voir la note du modèle de données).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnneeScolaire(Base):
    __tablename__ = "annee_scolaire"
    __table_args__ = (
        CheckConstraint("date_fin > date_debut", name="ck_annee_dates"),
        # Une seule année active à la fois (§1 de docs/02-modele-donnees.md, D5 de
        # docs/03-decisions-ouvertes.md) : index unique partiel, pas une simple
        # colonne — la contrainte est vraie même si le code applicatif a un bug.
        Index("ux_annee_active", "est_active", unique=True, postgresql_where=text("est_active")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    libelle: Mapped[str] = mapped_column(String(9), unique=True)
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    est_active: Mapped[bool] = mapped_column(Boolean, default=False)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Niveau(Base):
    __tablename__ = "niveau"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60))
    ordre: Mapped[int] = mapped_column(SmallInteger, unique=True)


class Matiere(Base):
    __tablename__ = "matiere"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    libelle: Mapped[str] = mapped_column(String(80))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Parametre(Base):
    __tablename__ = "parametre"

    cle: Mapped[str] = mapped_column(String(60), primary_key=True)
    valeur: Mapped[str] = mapped_column(String)
    type_valeur: Mapped[str] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TarifEleve(Base):
    __tablename__ = "tarif_eleve"
    __table_args__ = (
        CheckConstraint("montant_cents >= 0", name="ck_tarif_eleve_positif"),
        UniqueConstraint("annee_scolaire_id", "niveau_code", "matiere_id", name="ux_tarif_eleve"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    annee_scolaire_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("annee_scolaire.id"))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TarifPack(Base):
    """Forfait couvrant toutes les matières tarifées d'un niveau — voir
    `ModeFacturation.PACK` dans `app/modules/eleves/models.py`. Clé (année,
    niveau) seulement, pas de matière : contrairement à `tarif_eleve`, il
    n'y a qu'un montant par niveau."""

    __tablename__ = "tarif_pack"
    __table_args__ = (
        CheckConstraint("montant_cents >= 0", name="ck_tarif_pack_positif"),
        UniqueConstraint("annee_scolaire_id", "niveau_code", name="ux_tarif_pack"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    annee_scolaire_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("annee_scolaire.id"))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    montant_cents: Mapped[int] = mapped_column(BigInteger)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TarifProfesseur(Base):
    __tablename__ = "tarif_professeur"
    __table_args__ = (
        CheckConstraint("montant_par_eleve_cents >= 0", name="ck_tarif_prof_positif"),
        UniqueConstraint("annee_scolaire_id", "niveau_code", "matiere_id", name="ux_tarif_prof"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    annee_scolaire_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("annee_scolaire.id"))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    montant_par_eleve_cents: Mapped[int] = mapped_column(BigInteger)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
