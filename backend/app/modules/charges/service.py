"""Service du module charges — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable, ValidationMetier
from app.modules.audit.service import journaliser
from app.modules.charges.models import CategorieCharge, Charge
from app.modules.charges.repository import CategorieChargeRepository, ChargeRepository
from app.modules.charges.schemas import (
    CategorieChargeCreation,
    CategorieChargeMiseAJour,
    EvolutionChargesReponse,
    PointChargeMensuel,
)
from app.modules.paiements.models import ModePaiement
from app.modules.referentiel.repository import AnneeScolaireRepository
from app.shared import stockage

# Une année scolaire commence toujours en septembre (même convention que le
# graphe d'évolution des effectifs du dashboard) — 9,10,11,12 puis 1..8.
_MOIS_ANNEE_SCOLAIRE = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]


class CategorieChargeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._categories = CategorieChargeRepository(session)

    async def lister(self) -> list[CategorieCharge]:
        return await self._categories.lister()

    async def creer(self, donnees: CategorieChargeCreation) -> CategorieCharge:
        if await self._categories.get_by_libelle(donnees.libelle) is not None:
            raise ConflitMetier(f"La catégorie {donnees.libelle!r} existe déjà.")

        categorie = await self._categories.creer(CategorieCharge(libelle=donnees.libelle))
        await self._session.commit()
        return categorie

    async def mettre_a_jour(
        self, categorie_id: int, donnees: CategorieChargeMiseAJour
    ) -> CategorieCharge:
        categorie = await self._categories.get_by_id(categorie_id)
        if categorie is None:
            raise RessourceIntrouvable(f"Catégorie {categorie_id} introuvable.")

        for champ, valeur in donnees.model_dump(exclude_unset=True).items():
            setattr(categorie, champ, valeur)

        await self._session.commit()
        return categorie


class ChargeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._charges = ChargeRepository(session)
        self._categories = CategorieChargeRepository(session)
        self._annees = AnneeScolaireRepository(session)

    async def creer(
        self,
        *,
        categorie_id: int,
        description: str,
        montant_cents: int,
        date_charge: date,
        periode: str,
        mode_paiement: ModePaiement,
        justificatif: bytes | None,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Charge:
        if await self._categories.get_by_id(categorie_id) is None:
            raise RessourceIntrouvable(f"Catégorie {categorie_id} introuvable.")

        justificatif_chemin: str | None = None
        justificatif_type: str | None = None
        if justificatif is not None:
            justificatif_chemin = f"charges/{uuid.uuid4().hex}"
            justificatif_type = stockage.sauvegarder(justificatif, justificatif_chemin)

        charge = await self._charges.creer(
            Charge(
                categorie_id=categorie_id,
                description=description,
                montant_cents=montant_cents,
                date_charge=date_charge,
                periode=periode,
                mode_paiement=mode_paiement,
                justificatif_chemin=justificatif_chemin,
                justificatif_type=justificatif_type,
                cree_par=utilisateur_id,
            )
        )

        await journaliser(
            self._session,
            action="CREATION",
            entite="charge",
            entite_id=charge.id,
            utilisateur_id=utilisateur_id,
            apres={
                "categorie_id": categorie_id,
                "montant_cents": montant_cents,
                "periode": periode,
            },
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return charge

    async def obtenir(self, charge_id: int) -> Charge:
        charge = await self._charges.get_by_id(charge_id)
        if charge is None:
            raise RessourceIntrouvable(f"Charge {charge_id} introuvable.")
        return charge

    async def obtenir_justificatif(self, charge_id: int) -> tuple[bytes, str]:
        charge = await self.obtenir(charge_id)
        if charge.justificatif_chemin is None or charge.justificatif_type is None:
            raise RessourceIntrouvable(f"Charge {charge_id} n'a pas de justificatif.")
        return stockage.lire(charge.justificatif_chemin), charge.justificatif_type

    async def lister(self, *, periode: str | None, categorie_id: int | None) -> list[Charge]:
        return await self._charges.lister(periode=periode, categorie_id=categorie_id)

    async def totaux(self, periode: str) -> tuple[int, list[tuple[int, int]]]:
        total = await self._charges.total_periode(periode)
        par_categorie = await self._charges.total_par_categorie(periode)
        return total, par_categorie

    async def evolution_mensuelle(self) -> EvolutionChargesReponse:
        annee_active = next((a for a in await self._annees.lister() if a.est_active), None)
        if annee_active is None:
            raise ValidationMetier(
                "Aucune année scolaire active — le graphe des charges n'a rien à afficher."
            )

        annee_debut = int(annee_active.libelle.split("-")[0])
        periodes = []
        for mois in _MOIS_ANNEE_SCOLAIRE:
            annee_civile = annee_debut if mois >= 9 else annee_debut + 1
            periodes.append(f"{annee_civile:04d}-{mois:02d}")

        totaux_par_periode = await self._charges.total_par_periodes(periodes)
        points = [
            PointChargeMensuel(mois=mois, total_cents=totaux_par_periode.get(periode, 0))
            for mois, periode in zip(_MOIS_ANNEE_SCOLAIRE, periodes, strict=True)
        ]
        return EvolutionChargesReponse(annee_scolaire=annee_active.libelle, points=points)

    async def annuler(self, charge_id: int, utilisateur_id: int, adresse_ip: str | None) -> Charge:
        charge = await self.obtenir(charge_id)
        if charge.annule_le is not None:
            raise ConflitMetier("Cette charge est déjà annulée.")

        charge.annule_le = datetime.now(UTC)

        await journaliser(
            self._session,
            action="ANNULATION",
            entite="charge",
            entite_id=charge.id,
            utilisateur_id=utilisateur_id,
            avant={"annule_le": None},
            apres={"annule_le": charge.annule_le.isoformat()},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return charge
