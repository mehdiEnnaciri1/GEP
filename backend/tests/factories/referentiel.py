"""Construction de données de référentiel pour les tests (années, niveaux,
matières, tarifs) — réutilisé par les tests eleves et paiements."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.referentiel.models import (
    AnneeScolaire,
    Matiere,
    Niveau,
    TarifEleve,
    TarifPack,
    TarifProfesseur,
)


async def creer_annee_scolaire(
    session: AsyncSession,
    *,
    libelle: str = "2025-2026",
    date_debut: date = date(2025, 9, 1),
    date_fin: date = date(2026, 6, 30),
    active: bool = True,
) -> AnneeScolaire:
    annee = AnneeScolaire(
        libelle=libelle, date_debut=date_debut, date_fin=date_fin, est_active=active
    )
    session.add(annee)
    await session.commit()
    await session.refresh(annee)
    return annee


async def creer_niveau(
    session: AsyncSession,
    *,
    code: str = "1BAC",
    libelle: str = "1ère année baccalauréat",
    ordre: int = 5,
) -> Niveau:
    niveau = Niveau(code=code, libelle=libelle, ordre=ordre)
    session.add(niveau)
    await session.commit()
    return niveau


async def creer_matiere(
    session: AsyncSession, *, code: str = "MATH", libelle: str = "Mathématiques"
) -> Matiere:
    matiere = Matiere(code=code, libelle=libelle)
    session.add(matiere)
    await session.commit()
    await session.refresh(matiere)
    return matiere


async def creer_tarif_eleve(
    session: AsyncSession,
    *,
    annee_scolaire_id: int,
    niveau_code: str,
    matiere_id: int,
    montant_cents: int = 20000,
) -> TarifEleve:
    tarif = TarifEleve(
        annee_scolaire_id=annee_scolaire_id,
        niveau_code=niveau_code,
        matiere_id=matiere_id,
        montant_cents=montant_cents,
    )
    session.add(tarif)
    await session.commit()
    return tarif


async def creer_tarif_pack(
    session: AsyncSession,
    *,
    annee_scolaire_id: int,
    niveau_code: str,
    montant_cents: int = 50000,
) -> TarifPack:
    tarif = TarifPack(
        annee_scolaire_id=annee_scolaire_id, niveau_code=niveau_code, montant_cents=montant_cents
    )
    session.add(tarif)
    await session.commit()
    return tarif


async def creer_tarif_professeur(
    session: AsyncSession,
    *,
    annee_scolaire_id: int,
    niveau_code: str,
    matiere_id: int,
    montant_par_eleve_cents: int = 3500,
) -> TarifProfesseur:
    tarif = TarifProfesseur(
        annee_scolaire_id=annee_scolaire_id,
        niveau_code=niveau_code,
        matiere_id=matiere_id,
        montant_par_eleve_cents=montant_par_eleve_cents,
    )
    session.add(tarif)
    await session.commit()
    return tarif
