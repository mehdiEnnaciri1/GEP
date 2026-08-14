"""Service d'écriture du journal d'audit — appelé par les autres modules.

Ne lève jamais d'exception métier : une écriture d'audit fait partie de la
même transaction que l'action journalisée (voir §3 de docs/01-architecture.md),
elle ne doit jamais être l'endroit où une opération légitime échoue.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import JournalAudit
from app.modules.audit.repository import JournalAuditRepository


async def journaliser(
    session: AsyncSession,
    *,
    action: str,
    entite: str,
    entite_id: int | None = None,
    utilisateur_id: int | None = None,
    avant: dict[str, object] | None = None,
    apres: dict[str, object] | None = None,
    adresse_ip: str | None = None,
) -> None:
    entree = JournalAudit(
        utilisateur_id=utilisateur_id,
        action=action,
        entite=entite,
        entite_id=entite_id,
        avant=avant,
        apres=apres,
        adresse_ip=adresse_ip,
    )
    await JournalAuditRepository(session).ajouter(entree)
