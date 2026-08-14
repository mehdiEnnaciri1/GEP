"""Modèle `journal_audit` — voir docs/02-modele-donnees.md §7.

Ajout seul : ni `UPDATE` ni `DELETE` applicatif sur cette table. La révocation
des privilèges au niveau du rôle Postgres (§7 du modèle de données) suppose un
rôle applicatif distinct du rôle propriétaire des migrations ; ce projet n'a
qu'un seul rôle Postgres pour l'instant (simplicité délibérée, §1 de
docs/01-architecture.md). À mettre en place avant l'étape 10 (mise en
production) si un rôle applicatif restreint est introduit.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JournalAudit(Base):
    __tablename__ = "journal_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    utilisateur_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("utilisateur.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(30))
    entite: Mapped[str] = mapped_column(String(40))
    entite_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    avant: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    apres: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    adresse_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
