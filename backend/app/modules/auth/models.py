"""Modèle `utilisateur` — voir docs/02-modele-donnees.md §2."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoleUtilisateur(enum.StrEnum):
    ADMIN = "ADMIN"
    CAISSIER = "CAISSIER"
    PROFESSEUR = "PROFESSEUR"


class Utilisateur(Base):
    __tablename__ = "utilisateur"
    __table_args__ = (
        CheckConstraint(
            "(role = 'PROFESSEUR' AND professeur_id IS NOT NULL) "
            "OR (role <> 'PROFESSEUR' AND professeur_id IS NULL)",
            name="ck_prof_lie",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nom: Mapped[str] = mapped_column(String(80))
    prenom: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String)
    role: Mapped[RoleUtilisateur] = mapped_column(Enum(RoleUtilisateur, name="role_utilisateur"))
    # ⚠ La table `professeur` n'existe pas encore (étape 5 de la roadmap). Colonne
    # nullable, sans ForeignKey pour l'instant ; la FK sera ajoutée dans une
    # migration ultérieure quand `professeur` sera créée.
    professeur_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    derniere_connexion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
