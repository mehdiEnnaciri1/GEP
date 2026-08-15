"""En-tête `Idempotency-Key` — voir §6.4 de docs/01-architecture.md.

Le déduplication elle-même vit dans les services d'écriture financière : la
colonne `paiement.cle_idempotence` (UNIQUE) est la source de vérité, pas une
table de cache séparée. Ce module ne fait que lire l'en-tête HTTP.
"""

from __future__ import annotations

import uuid

from fastapi import Header

from app.core.exceptions import ValidationMetier


def obtenir_cle_idempotence(
    idempotency_key: str | None = Header(default=None),
) -> uuid.UUID | None:
    if idempotency_key is None:
        return None
    try:
        return uuid.UUID(idempotency_key)
    except ValueError as exc:
        raise ValidationMetier("Idempotency-Key doit être un UUID valide.") from exc
