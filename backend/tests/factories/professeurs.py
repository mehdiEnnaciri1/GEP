"""Construction de professeurs et affectations pour les tests."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.professeurs.models import Affectation, Professeur


async def creer_professeur(
    session: AsyncSession,
    *,
    nom: str = "Alaoui",
    prenom: str = "Karim",
    telephone: str = "0600000001",
) -> Professeur:
    professeur = Professeur(nom=nom, prenom=prenom, telephone=telephone)
    session.add(professeur)
    await session.commit()
    await session.refresh(professeur)
    return professeur


async def creer_affectation(
    session: AsyncSession,
    *,
    professeur_id: int,
    matiere_id: int,
    niveau_code: str,
    annee_scolaire_id: int,
    date_debut: date = date(2025, 9, 1),
    date_fin: date | None = None,
) -> Affectation:
    affectation = Affectation(
        professeur_id=professeur_id,
        matiere_id=matiere_id,
        niveau_code=niveau_code,
        annee_scolaire_id=annee_scolaire_id,
        date_debut=date_debut,
        date_fin=date_fin,
    )
    session.add(affectation)
    await session.commit()
    await session.refresh(affectation)
    return affectation
