"""Point d'entrée de l'application FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.exceptions import enregistrer_gestionnaires_exceptions
from app.modules.auth.router import router as auth_router
from app.modules.charges.router import router as charges_router
from app.modules.eleves.router import router as eleves_router
from app.modules.paie.router import router as paie_router
from app.modules.paiements.router import router as paiements_router
from app.modules.professeurs.router import router as professeurs_router
from app.modules.referentiel.router import router as referentiel_router

app = FastAPI(title="GEP — API")

enregistrer_gestionnaires_exceptions(app)

# Tout routeur de module est monté ici avec prefix="/api" — même origine que
# le front en dev (proxy Vite) et en production (nginx). Seul /health reste à
# la racine : c'est ce qu'interroge le healthcheck Docker Compose du service api.
app.include_router(auth_router, prefix="/api")
app.include_router(referentiel_router, prefix="/api")
app.include_router(eleves_router, prefix="/api")
app.include_router(paiements_router, prefix="/api")
app.include_router(professeurs_router, prefix="/api")
app.include_router(paie_router, prefix="/api")
app.include_router(charges_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"statut": "ok"}
