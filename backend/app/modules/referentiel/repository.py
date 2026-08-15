"""Requêtes SQLAlchemy du référentiel. Aucune règle métier ici — notamment,
la désactivation des autres années à l'activation d'une année est orchestrée
par le service, pas ici."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.referentiel.models import (
    AnneeScolaire,
    Matiere,
    Niveau,
    Parametre,
    TarifEleve,
    TarifProfesseur,
)


class AnneeScolaireRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister(self) -> list[AnneeScolaire]:
        resultat = await self._session.execute(
            select(AnneeScolaire).order_by(AnneeScolaire.date_debut.desc())
        )
        return list(resultat.scalars().all())

    async def get_by_id(self, annee_id: int) -> AnneeScolaire | None:
        return await self._session.get(AnneeScolaire, annee_id)

    async def get_by_libelle(self, libelle: str) -> AnneeScolaire | None:
        resultat = await self._session.execute(
            select(AnneeScolaire).where(AnneeScolaire.libelle == libelle)
        )
        return resultat.scalar_one_or_none()

    async def creer(self, annee: AnneeScolaire) -> AnneeScolaire:
        self._session.add(annee)
        await self._session.flush()
        return annee

    async def desactiver_toutes(self) -> None:
        await self._session.execute(update(AnneeScolaire).values(est_active=False))


class NiveauRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister(self) -> list[Niveau]:
        resultat = await self._session.execute(select(Niveau).order_by(Niveau.ordre))
        return list(resultat.scalars().all())

    async def existe(self, code: str) -> bool:
        return await self._session.get(Niveau, code) is not None


class MatiereRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister(self) -> list[Matiere]:
        resultat = await self._session.execute(select(Matiere).order_by(Matiere.libelle))
        return list(resultat.scalars().all())

    async def get_by_id(self, matiere_id: int) -> Matiere | None:
        return await self._session.get(Matiere, matiere_id)

    async def get_by_code(self, code: str) -> Matiere | None:
        resultat = await self._session.execute(select(Matiere).where(Matiere.code == code))
        return resultat.scalar_one_or_none()

    async def creer(self, matiere: Matiere) -> Matiere:
        self._session.add(matiere)
        await self._session.flush()
        return matiere


class ParametreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister(self) -> list[Parametre]:
        resultat = await self._session.execute(select(Parametre).order_by(Parametre.cle))
        return list(resultat.scalars().all())

    async def get_by_cle(self, cle: str) -> Parametre | None:
        return await self._session.get(Parametre, cle)

    async def creer(self, parametre: Parametre) -> Parametre:
        self._session.add(parametre)
        await self._session.flush()
        return parametre


class TarifEleveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister_par_annee(self, annee_scolaire_id: int) -> list[TarifEleve]:
        resultat = await self._session.execute(
            select(TarifEleve).where(TarifEleve.annee_scolaire_id == annee_scolaire_id)
        )
        return list(resultat.scalars().all())

    async def get_par_cle(
        self, annee_scolaire_id: int, niveau_code: str, matiere_id: int
    ) -> TarifEleve | None:
        resultat = await self._session.execute(
            select(TarifEleve).where(
                TarifEleve.annee_scolaire_id == annee_scolaire_id,
                TarifEleve.niveau_code == niveau_code,
                TarifEleve.matiere_id == matiere_id,
            )
        )
        return resultat.scalar_one_or_none()

    async def creer(self, tarif: TarifEleve) -> TarifEleve:
        self._session.add(tarif)
        await self._session.flush()
        return tarif


class TarifProfesseurRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lister_par_annee(self, annee_scolaire_id: int) -> list[TarifProfesseur]:
        resultat = await self._session.execute(
            select(TarifProfesseur).where(TarifProfesseur.annee_scolaire_id == annee_scolaire_id)
        )
        return list(resultat.scalars().all())

    async def get_par_cle(
        self, annee_scolaire_id: int, niveau_code: str, matiere_id: int
    ) -> TarifProfesseur | None:
        resultat = await self._session.execute(
            select(TarifProfesseur).where(
                TarifProfesseur.annee_scolaire_id == annee_scolaire_id,
                TarifProfesseur.niveau_code == niveau_code,
                TarifProfesseur.matiere_id == matiere_id,
            )
        )
        return resultat.scalar_one_or_none()

    async def creer(self, tarif: TarifProfesseur) -> TarifProfesseur:
        self._session.add(tarif)
        await self._session.flush()
        return tarif
