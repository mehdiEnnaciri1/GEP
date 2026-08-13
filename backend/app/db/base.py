"""Base déclarative et mixins communs à toutes les tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base ORM unique du projet. Alembic lit `Base.metadata` pour l'autogenerate :
    chaque module doit donc importer ses modèles quelque part avant que `env.py`
    ne soit exécuté (voir `app/db/base.py` du dépôt au fil de l'ajout des modules)."""


class MixinHorodatage:
    """`cree_le` / `modifie_le` — présents sur toute table (§conventions de
    `docs/02-modele-donnees.md`)."""

    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
