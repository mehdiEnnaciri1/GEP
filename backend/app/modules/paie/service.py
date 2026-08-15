"""Service du module paie — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md).

Le tarif professeur est lu une seule fois, à la génération, puis copié dans
`ligne_paie.tarif_unitaire_cents` (décision D1, même principe que
`inscription_matiere.tarif_mensuel_cents`) : une modification ultérieure du
référentiel n'a aucun effet sur les paies déjà générées.

Une paie `VALIDEE` ou `PAYEE` est verrouillée (voir CLAUDE.md) : toute
correction passe par `ajouter_ligne_ajustement`, appelée sur la paie de la
période SUIVANTE — jamais par une régénération de la paie verrouillée.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable
from app.modules.audit.service import journaliser
from app.modules.paie.models import LignePaie, PaieMensuelle, StatutPaie
from app.modules.paie.repository import (
    CompteurElevesRepository,
    LignePaieRepository,
    PaieMensuelleRepository,
)
from app.modules.paie.schemas import AjustementPaieRequete
from app.modules.paiements.models import ModePaiement
from app.modules.professeurs.repository import AffectationRepository, ProfesseurRepository
from app.modules.referentiel.repository import ParametreRepository, TarifProfesseurRepository
from app.shared.periode import dernier_jour, premier_jour

_BASE_CALCUL_PAR_DEFAUT = "inscrits"  # décision D4


class PaieService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._paies = PaieMensuelleRepository(session)
        self._lignes = LignePaieRepository(session)
        self._compteur = CompteurElevesRepository(session)
        self._professeurs = ProfesseurRepository(session)
        self._affectations = AffectationRepository(session)
        self._tarifs_professeur = TarifProfesseurRepository(session)
        self._parametres = ParametreRepository(session)

    async def _base_calcul(self) -> str:
        parametre = await self._parametres.get_by_cle("base_calcul_paie")
        return parametre.valeur if parametre is not None else _BASE_CALCUL_PAR_DEFAUT

    async def generer(self, periode: str, utilisateur_id: int, adresse_ip: str | None) -> int:
        borne_debut = premier_jour(periode)
        borne_fin = dernier_jour(periode)
        base_calcul = await self._base_calcul()
        compteur = 0

        for professeur in [p for p in await self._professeurs.lister() if p.actif]:
            affectations = await self._affectations.lister(professeur_id=professeur.id)
            affectations_actives = [
                a
                for a in affectations
                if a.date_debut <= borne_fin and (a.date_fin is None or a.date_fin >= borne_debut)
            ]
            if not affectations_actives:
                continue

            paie_existante = await self._paies.get_par_cle(professeur.id, periode)
            if paie_existante is not None:
                if paie_existante.statut != StatutPaie.BROUILLON:
                    raise ConflitMetier(
                        f"La paie de {professeur.prenom} {professeur.nom} pour {periode} est "
                        f"déjà {paie_existante.statut.value.lower()} — une correction passe par "
                        "une ligne d'ajustement sur la période suivante, jamais par une "
                        "régénération de la paie verrouillée."
                    )
                await self._lignes.supprimer_lignes_generees(paie_existante.id)
                paie = paie_existante
            else:
                paie = await self._paies.creer(
                    PaieMensuelle(professeur_id=professeur.id, periode=periode)
                )

            total = 0
            for affectation in affectations_actives:
                tarif = await self._tarifs_professeur.get_par_cle(
                    affectation.annee_scolaire_id, affectation.niveau_code, affectation.matiere_id
                )
                if tarif is None:
                    raise RessourceIntrouvable(
                        f"Aucun tarif professeur défini pour {affectation.niveau_code}/"
                        f"{affectation.matiere_id} — définissez-le dans le référentiel avant "
                        "de générer la paie."
                    )

                nombre_eleves = await self._compteur.compter(
                    niveau_code=affectation.niveau_code,
                    matiere_id=affectation.matiere_id,
                    annee_scolaire_id=affectation.annee_scolaire_id,
                    periode=periode,
                    base_calcul=base_calcul,
                )
                montant = nombre_eleves * tarif.montant_par_eleve_cents
                total += montant
                await self._lignes.creer(
                    LignePaie(
                        paie_id=paie.id,
                        matiere_id=affectation.matiere_id,
                        niveau_code=affectation.niveau_code,
                        nombre_eleves=nombre_eleves,
                        tarif_unitaire_cents=tarif.montant_par_eleve_cents,
                        montant_cents=montant,
                        est_ajustement=False,
                    )
                )

            # Les lignes d'ajustement survivent à une régénération (voir
            # LignePaieRepository.supprimer_lignes_generees) : leur montant
            # reste dû, il faut le reporter dans le nouveau total.
            total += sum(
                ligne.montant_cents
                for ligne in await self._lignes.lister_par_paie(paie.id)
                if ligne.est_ajustement
            )
            paie.total_cents = total
            compteur += 1

        await journaliser(
            self._session,
            action="CREATION",
            entite="paie_mensuelle",
            utilisateur_id=utilisateur_id,
            apres={"periode": periode, "nombre_generees": compteur},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return compteur

    async def lister(self, periode: str) -> list[PaieMensuelle]:
        return await self._paies.lister_par_periode(periode)

    async def lister_par_professeur(self, professeur_id: int) -> list[PaieMensuelle]:
        return await self._paies.lister_par_professeur(professeur_id)

    async def obtenir_detail(self, paie_id: int) -> tuple[PaieMensuelle, list[LignePaie]]:
        paie = await self._paies.get_by_id(paie_id)
        if paie is None:
            raise RessourceIntrouvable(f"Paie {paie_id} introuvable.")
        lignes = await self._lignes.lister_par_paie(paie_id)
        return paie, lignes

    async def valider(
        self, paie_id: int, utilisateur_id: int, adresse_ip: str | None
    ) -> PaieMensuelle:
        paie = await self._paies.get_by_id(paie_id)
        if paie is None:
            raise RessourceIntrouvable(f"Paie {paie_id} introuvable.")
        if paie.statut != StatutPaie.BROUILLON:
            raise ConflitMetier(
                f"Cette paie est déjà {paie.statut.value.lower()} — "
                "seule une paie BROUILLON peut être validée."
            )

        paie.statut = StatutPaie.VALIDEE
        paie.validee_le = datetime.now(UTC)
        paie.validee_par = utilisateur_id

        await journaliser(
            self._session,
            action="VALIDATION",
            entite="paie_mensuelle",
            entite_id=paie.id,
            utilisateur_id=utilisateur_id,
            avant={"statut": "BROUILLON"},
            apres={"statut": "VALIDEE"},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return paie

    async def marquer_payee(
        self,
        paie_id: int,
        date_paiement: date,
        mode_paiement: ModePaiement,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> PaieMensuelle:
        paie = await self._paies.get_by_id(paie_id)
        if paie is None:
            raise RessourceIntrouvable(f"Paie {paie_id} introuvable.")
        if paie.statut != StatutPaie.VALIDEE:
            raise ConflitMetier("Seule une paie VALIDEE peut être marquée payée.")

        paie.statut = StatutPaie.PAYEE
        paie.payee_le = date_paiement
        paie.mode_paiement = mode_paiement

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="paie_mensuelle",
            entite_id=paie.id,
            utilisateur_id=utilisateur_id,
            avant={"statut": "VALIDEE"},
            apres={"statut": "PAYEE", "mode_paiement": mode_paiement.value},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return paie

    async def ajouter_ligne_ajustement(
        self, donnees: AjustementPaieRequete, utilisateur_id: int, adresse_ip: str | None
    ) -> LignePaie:
        paie = await self._paies.get_par_cle(donnees.professeur_id, donnees.periode)
        if paie is None:
            raise RessourceIntrouvable(
                f"Aucune paie pour le professeur {donnees.professeur_id} en {donnees.periode} — "
                "générez d'abord la paie de cette période avant d'y ajouter un ajustement."
            )

        lignes_existantes = await self._lignes.lister_par_paie(paie.id)
        if any(
            ligne.est_ajustement
            and ligne.matiere_id == donnees.matiere_id
            and ligne.niveau_code == donnees.niveau_code
            for ligne in lignes_existantes
        ):
            raise ConflitMetier(
                "Un ajustement existe déjà pour ce couple (matière, niveau) sur cette période."
            )

        ligne = await self._lignes.creer(
            LignePaie(
                paie_id=paie.id,
                matiere_id=donnees.matiere_id,
                niveau_code=donnees.niveau_code,
                nombre_eleves=0,
                tarif_unitaire_cents=0,
                montant_cents=donnees.montant_cents,
                est_ajustement=True,
                motif_ajustement=donnees.motif,
            )
        )
        paie.total_cents += donnees.montant_cents

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="paie_mensuelle",
            entite_id=paie.id,
            utilisateur_id=utilisateur_id,
            apres={"ligne_ajustement_cents": donnees.montant_cents, "motif": donnees.motif},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return ligne
