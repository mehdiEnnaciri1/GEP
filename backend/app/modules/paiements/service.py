"""Service du module paiements — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md).

Le statut d'une échéance est toujours RECALCULÉ depuis (montant_du,
montant_payé) via `calculer_statut_echeance`, jamais mis à jour par
transition ad hoc (NON_PAYE → PARTIEL → PAYE) : c'est ce qui rend
l'annulation sûre — encaisser et annuler appellent la même fonction pure
après avoir ajusté `montant_paye_cents` dans un sens ou dans l'autre.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable, ValidationMetier
from app.modules.audit.service import journaliser
from app.modules.eleves.models import StatutFrais
from app.modules.eleves.repository import (
    EleveRepository,
    FraisInscriptionRepository,
    InscriptionMatiereRepository,
)
from app.modules.paiements.models import (
    Echeance,
    LigneEcheance,
    ModePaiement,
    Paiement,
    StatutEcheance,
    TypePaiement,
)
from app.modules.paiements.repository import EcheanceRepository, PaiementRepository
from app.shared.periode import dernier_jour, premier_jour


def calculer_statut_echeance(montant_du_cents: int, montant_paye_cents: int) -> StatutEcheance:
    """§8.2 de docs/02-modele-donnees.md. Le trop-perçu (payé > dû) reste PAYE,
    délibérément — signalé ailleurs, régularisé par un avoir (hors périmètre)."""
    if montant_paye_cents <= 0:
        return StatutEcheance.NON_PAYE
    if montant_paye_cents < montant_du_cents:
        return StatutEcheance.PARTIEL
    return StatutEcheance.PAYE


class PaiementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._paiements = PaiementRepository(session)
        self._echeances = EcheanceRepository(session)
        self._eleves = EleveRepository(session)
        self._inscriptions = InscriptionMatiereRepository(session)
        self._frais = FraisInscriptionRepository(session)

    async def _generer_numero_recu(self, annee: int) -> str:
        compte = await self._paiements.compter_annee(annee)
        return f"R-{annee}-{compte + 1:06d}"

    async def encaisser_frais_inscription(
        self,
        *,
        eleve_id: int,
        montant_cents: int,
        mode: ModePaiement,
        date_paiement: date,
        cle_idempotence: uuid.UUID | None,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Paiement:
        if cle_idempotence is not None:
            existant = await self._paiements.get_by_cle_idempotence(cle_idempotence)
            if existant is not None:
                return existant

        frais = await self._frais.get_by_eleve(eleve_id)
        if frais is None:
            raise RessourceIntrouvable(f"Frais d'inscription introuvables pour l'élève {eleve_id}.")
        if frais.statut == StatutFrais.PAYE:
            raise ConflitMetier("Les frais d'inscription sont déjà payés.")
        if montant_cents != frais.montant_cents:
            raise ValidationMetier(
                f"Le montant doit correspondre exactement aux frais d'inscription "
                f"({frais.montant_cents} centimes)."
            )

        numero_recu = await self._generer_numero_recu(date_paiement.year)
        paiement = await self._paiements.creer(
            Paiement(
                numero_recu=numero_recu,
                eleve_id=eleve_id,
                type=TypePaiement.INSCRIPTION,
                periode=None,
                montant_cents=montant_cents,
                date_paiement=date_paiement,
                mode=mode,
                cree_par=utilisateur_id,
                cle_idempotence=cle_idempotence,
            )
        )

        frais.statut = StatutFrais.PAYE
        frais.date_paiement = date_paiement
        frais.paiement_id = paiement.id

        await journaliser(
            self._session,
            action="CREATION",
            entite="paiement",
            entite_id=paiement.id,
            utilisateur_id=utilisateur_id,
            apres={"type": "INSCRIPTION", "montant_cents": montant_cents, "eleve_id": eleve_id},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return paiement

    async def encaisser_mensualite(
        self,
        *,
        eleve_id: int,
        periode: str,
        montant_cents: int,
        mode: ModePaiement,
        date_paiement: date,
        cle_idempotence: uuid.UUID | None,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Paiement:
        if cle_idempotence is not None:
            existant = await self._paiements.get_by_cle_idempotence(cle_idempotence)
            if existant is not None:
                return existant

        echeance = await self._echeances.get_by_eleve_et_periode(eleve_id, periode)
        if echeance is None:
            raise RessourceIntrouvable(
                f"Aucune échéance générée pour l'élève {eleve_id} en {periode}."
            )

        numero_recu = await self._generer_numero_recu(date_paiement.year)
        paiement = await self._paiements.creer(
            Paiement(
                numero_recu=numero_recu,
                eleve_id=eleve_id,
                type=TypePaiement.MENSUALITE,
                periode=periode,
                montant_cents=montant_cents,
                date_paiement=date_paiement,
                mode=mode,
                cree_par=utilisateur_id,
                cle_idempotence=cle_idempotence,
            )
        )

        echeance.montant_paye_cents += montant_cents
        echeance.statut = calculer_statut_echeance(
            echeance.montant_du_cents, echeance.montant_paye_cents
        )

        await journaliser(
            self._session,
            action="CREATION",
            entite="paiement",
            entite_id=paiement.id,
            utilisateur_id=utilisateur_id,
            apres={
                "type": "MENSUALITE",
                "montant_cents": montant_cents,
                "eleve_id": eleve_id,
                "periode": periode,
            },
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return paiement

    async def annuler(
        self, paiement_id: int, motif: str, utilisateur_id: int, adresse_ip: str | None
    ) -> Paiement:
        paiement = await self._paiements.get_by_id(paiement_id)
        if paiement is None:
            raise RessourceIntrouvable(f"Paiement {paiement_id} introuvable.")
        if paiement.annule_le is not None:
            raise ConflitMetier("Ce paiement est déjà annulé.")

        if paiement.type == TypePaiement.INSCRIPTION:
            frais = await self._frais.get_by_eleve(paiement.eleve_id)
            if frais is not None and frais.paiement_id == paiement.id:
                frais.statut = StatutFrais.NON_PAYE
                frais.date_paiement = None
                frais.paiement_id = None
        else:
            assert paiement.periode is not None  # garanti par ck_paiement_periode
            echeance = await self._echeances.get_by_eleve_et_periode(
                paiement.eleve_id, paiement.periode
            )
            if echeance is not None:
                echeance.montant_paye_cents = max(
                    0, echeance.montant_paye_cents - paiement.montant_cents
                )
                echeance.statut = calculer_statut_echeance(
                    echeance.montant_du_cents, echeance.montant_paye_cents
                )

        paiement.annule_le = datetime.now(UTC)
        paiement.annule_par = utilisateur_id
        paiement.motif_annulation = motif

        await journaliser(
            self._session,
            action="ANNULATION",
            entite="paiement",
            entite_id=paiement.id,
            utilisateur_id=utilisateur_id,
            avant={"annule_le": None},
            apres={"motif_annulation": motif},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return paiement

    async def lister_impayes(self, periode: str) -> list[Echeance]:
        return await self._echeances.lister_impayes(periode)

    async def historique_eleve(self, eleve_id: int) -> list[Paiement]:
        return await self._paiements.lister_par_eleve(eleve_id)

    async def generer_echeances(
        self, periode: str, utilisateur_id: int, adresse_ip: str | None
    ) -> int:
        borne_debut = premier_jour(periode)
        borne_fin = dernier_jour(periode)
        compteur = 0

        for eleve in await self._eleves.lister_actifs():
            if await self._echeances.get_by_eleve_et_periode(eleve.id, periode) is not None:
                continue

            inscriptions = await self._inscriptions.lister_par_eleve(eleve.id)
            inscriptions_actives = [
                i
                for i in inscriptions
                if i.date_debut <= borne_fin and (i.date_fin is None or i.date_fin >= borne_debut)
            ]
            if not inscriptions_actives:
                continue

            montant_du = sum(i.tarif_mensuel_cents for i in inscriptions_actives)
            echeance = await self._echeances.creer(
                Echeance(
                    eleve_id=eleve.id,
                    periode=periode,
                    montant_du_cents=montant_du,
                    montant_paye_cents=0,
                    statut=StatutEcheance.NON_PAYE,
                )
            )
            for inscription in inscriptions_actives:
                await self._echeances.creer_ligne(
                    LigneEcheance(
                        echeance_id=echeance.id,
                        matiere_id=inscription.matiere_id,
                        tarif_cents=inscription.tarif_mensuel_cents,
                    )
                )
            compteur += 1

        await journaliser(
            self._session,
            action="CREATION",
            entite="echeance",
            utilisateur_id=utilisateur_id,
            apres={"periode": periode, "nombre_generees": compteur},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return compteur
