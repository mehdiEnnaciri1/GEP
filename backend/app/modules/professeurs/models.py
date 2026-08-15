"""Professeurs et affectations — voir docs/02-modele-donnees.md §5."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Professeur(Base):
    __tablename__ = "professeur"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nom: Mapped[str] = mapped_column(String(80))
    prenom: Mapped[str] = mapped_column(String(80))
    telephone: Mapped[str] = mapped_column(String(20))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Affectation(Base):
    """Un professeur enseigne une matière sur un niveau, pour une année scolaire.

    ⚠ CONTRAINTE STRUCTURANTE — décision D3 de docs/03-decisions-ouvertes.md,
    TOUJOURS NON CONFIRMÉE PAR LE CLIENT. `ux_affectation_unique` rend
    impossible d'avoir deux professeurs sur le même couple (année, matière,
    niveau) : la formule de paie du §7.1 (`tarif × nombre d'élèves du couple`)
    n'est bien définie que s'il y a un seul professeur par couple — sinon
    chacun serait payé sur la totalité des élèves et le centre paierait deux
    fois. Si le centre a réellement deux professeurs sur un même couple (deux
    groupes, deux créneaux), cette contrainte doit sauter : il faut alors
    introduire la notion de groupe (§12 du cahier des charges) et RE-DÉFINIR
    le calcul de paie autour du groupe plutôt que du couple (matière, niveau).
    Ce n'est pas une évolution mineure — ne pas contourner la contrainte
    (ex. deux affectations avec des dates qui se chevauchent) sans avoir fait
    ce travail de modélisation.
    """

    __tablename__ = "affectation"
    __table_args__ = (
        UniqueConstraint(
            "annee_scolaire_id", "matiere_id", "niveau_code", name="ux_affectation_unique"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    professeur_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("professeur.id"))
    matiere_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matiere.id"))
    niveau_code: Mapped[str] = mapped_column(String(5), ForeignKey("niveau.code"))
    annee_scolaire_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("annee_scolaire.id"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["Professeur", "Affectation"]
