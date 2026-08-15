"""Service du module eleves — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RessourceIntrouvable, ValidationMetier
from app.modules.audit.service import journaliser
from app.modules.eleves.models import Eleve, FraisInscription, InscriptionMatiere, StatutEleve
from app.modules.eleves.repository import (
    EleveRepository,
    FraisInscriptionRepository,
    InscriptionMatiereRepository,
)
from app.modules.eleves.schemas import EleveCreation, EleveMiseAJour
from app.modules.referentiel.repository import (
    AnneeScolaireRepository,
    MatiereRepository,
    NiveauRepository,
    ParametreRepository,
    TarifEleveRepository,
)

_MONTANT_FRAIS_PAR_DEFAUT_CENTS = 5000


class EleveService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._eleves = EleveRepository(session)
        self._inscriptions = InscriptionMatiereRepository(session)
        self._frais = FraisInscriptionRepository(session)
        self._annees = AnneeScolaireRepository(session)
        self._niveaux = NiveauRepository(session)
        self._matieres = MatiereRepository(session)
        self._tarifs_eleve = TarifEleveRepository(session)
        self._parametres = ParametreRepository(session)

    async def creer(
        self, donnees: EleveCreation, utilisateur_id: int, adresse_ip: str | None
    ) -> tuple[Eleve, list[InscriptionMatiere], FraisInscription]:
        annee_active = next((a for a in await self._annees.lister() if a.est_active), None)
        if annee_active is None:
            raise ValidationMetier(
                "Aucune année scolaire active — activez une année avant de créer un élève."
            )

        if not await self._niveaux.existe(donnees.niveau_code):
            raise RessourceIntrouvable(f"Niveau {donnees.niveau_code} introuvable.")

        # Le matricule embarque l'année de DÉBUT de l'année scolaire active (le
        # cahier des charges ne précise pas la règle exacte) : tous les élèves
        # inscrits pendant l'année scolaire 2025-2026 portent E-2025-xxxx, que
        # l'inscription ait lieu en septembre ou en février. Le numéro de
        # séquence, lui, est global (SEQUENCE Postgres, voir repository) : il
        # ne repart pas à 1 à chaque nouvelle année, pour rester atomique sous
        # concurrence.
        annee_matricule = annee_active.date_debut.year
        numero = await self._eleves.prochain_numero_matricule()
        matricule = f"E-{annee_matricule}-{numero:04d}"

        eleve = await self._eleves.creer(
            Eleve(
                matricule=matricule,
                nom=donnees.nom,
                prenom=donnees.prenom,
                telephone_eleve=donnees.telephone_eleve,
                telephone_parent=donnees.telephone_parent,
                niveau_code=donnees.niveau_code,
                annee_scolaire_id=annee_active.id,
                date_inscription=donnees.date_inscription,
                observation=donnees.observation,
                cree_par=utilisateur_id,
            )
        )

        inscriptions = []
        for matiere_id in donnees.matiere_ids:
            if await self._matieres.get_by_id(matiere_id) is None:
                raise RessourceIntrouvable(f"Matière {matiere_id} introuvable.")

            tarif = await self._tarifs_eleve.get_par_cle(
                annee_active.id, donnees.niveau_code, matiere_id
            )
            if tarif is None:
                raise RessourceIntrouvable(
                    f"Aucun tarif défini pour la matière {matiere_id} en {donnees.niveau_code} "
                    f"pour l'année {annee_active.libelle} — définissez-le dans le référentiel "
                    "avant d'inscrire un élève."
                )

            inscriptions.append(
                await self._inscriptions.creer(
                    InscriptionMatiere(
                        eleve_id=eleve.id,
                        matiere_id=matiere_id,
                        tarif_mensuel_cents=tarif.montant_cents,
                        date_debut=donnees.date_inscription,
                        cree_par=utilisateur_id,
                    )
                )
            )

        parametre_frais = await self._parametres.get_by_cle("frais_inscription_cents")
        montant_frais = (
            int(parametre_frais.valeur) if parametre_frais else _MONTANT_FRAIS_PAR_DEFAUT_CENTS
        )
        frais = await self._frais.creer(
            FraisInscription(eleve_id=eleve.id, montant_cents=montant_frais)
        )

        await journaliser(
            self._session,
            action="CREATION",
            entite="eleve",
            entite_id=eleve.id,
            utilisateur_id=utilisateur_id,
            apres={"matricule": matricule, "nom": donnees.nom, "prenom": donnees.prenom},
            adresse_ip=adresse_ip,
        )

        await self._session.commit()
        return eleve, inscriptions, frais

    async def obtenir_detail(
        self, eleve_id: int
    ) -> tuple[Eleve, list[InscriptionMatiere], FraisInscription | None]:
        eleve = await self._eleves.get_by_id(eleve_id)
        if eleve is None:
            raise RessourceIntrouvable(f"Élève {eleve_id} introuvable.")

        inscriptions = await self._inscriptions.lister_par_eleve(eleve_id)
        frais = await self._frais.get_by_eleve(eleve_id)
        return eleve, inscriptions, frais

    async def lister(
        self,
        *,
        recherche: str | None,
        niveau_code: str | None,
        statut: StatutEleve | None,
        page: int,
        taille: int,
    ) -> tuple[list[Eleve], int]:
        return await self._eleves.lister(
            recherche=recherche, niveau_code=niveau_code, statut=statut, page=page, taille=taille
        )

    async def mettre_a_jour(
        self,
        eleve_id: int,
        donnees: EleveMiseAJour,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Eleve:
        eleve = await self._eleves.get_by_id(eleve_id)
        if eleve is None:
            raise RessourceIntrouvable(f"Élève {eleve_id} introuvable.")

        champs = donnees.model_dump(exclude_unset=True)
        avant = {champ: getattr(eleve, champ) for champ in champs}
        for champ, valeur in champs.items():
            setattr(eleve, champ, valeur)

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="eleve",
            entite_id=eleve.id,
            utilisateur_id=utilisateur_id,
            avant=avant,
            apres=champs,
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return eleve

    async def changer_statut(
        self,
        eleve_id: int,
        nouveau_statut: StatutEleve,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Eleve:
        eleve = await self._eleves.get_by_id(eleve_id)
        if eleve is None:
            raise RessourceIntrouvable(f"Élève {eleve_id} introuvable.")

        ancien_statut = eleve.statut
        eleve.statut = nouveau_statut

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="eleve",
            entite_id=eleve.id,
            utilisateur_id=utilisateur_id,
            avant={"statut": ancien_statut.value},
            apres={"statut": nouveau_statut.value},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return eleve
