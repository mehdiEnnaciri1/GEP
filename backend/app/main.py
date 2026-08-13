"""Point d'entrée de l'application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.exceptions import enregistrer_gestionnaires_exceptions

app = FastAPI(title="GEP — API")

enregistrer_gestionnaires_exceptions(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"statut": "ok"}
