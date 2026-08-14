"""Point d'entrée de l'application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.exceptions import enregistrer_gestionnaires_exceptions
from app.modules.auth.router import router as auth_router

app = FastAPI(title="GEP — API")

enregistrer_gestionnaires_exceptions(app)

# Tout routeur de module est monté ici avec prefix="/api" (ex. :
# app.include_router(eleves.router, prefix="/api")) — même origine que le
# front en dev (proxy Vite) et en production (nginx). Seul /health reste à la
# racine : c'est ce qu'interroge le healthcheck Docker Compose du service api.
app.include_router(auth_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"statut": "ok"}
