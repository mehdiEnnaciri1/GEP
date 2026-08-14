"""Écriture dans `journal_audit`. Ajout seul — aucune méthode de mise à jour
ou de suppression n'existe ici, volontairement (voir models.py)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import JournalAudit


class JournalAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ajouter(self, entree: JournalAudit) -> None:
        self._session.add(entree)
        await self._session.flush()
