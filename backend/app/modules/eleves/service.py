"""Service du module eleves — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable, ValidationMetier
from app.modules.audit.service import journaliser
from app.modules.eleves.models import Eleve, FraisInscription, InscriptionMatiere, StatutEleve
from app.modules.eleves.repository import (
    EleveRepository,
    FraisInscriptionRepository,
    InscriptionMatiereRepository,
)
from app.modules.eleves.schemas import DefinirPack, DefinirReduction, EleveCreation, EleveMiseAJour
from app.modules.referentiel.models import TarifPack
from app.modules.referentiel.repository import (
    AnneeScolaireRepository,
    MatiereRepository,
    NiveauRepository,
    ParametreRepository,
    TarifEleveRepository,
    TarifPackRepository,
)
from app.shared.periode import FUSEAU_HORAIRE_CENTRE

_MONTANT_FRAIS_PAR_DEFAUT_CENTS = 5000


def _fractionner_tarif_pack(tarif_pack: TarifPack, matiere_ids: list[int]) -> dict[int, int]:
    """Répartit `tarif_pack.montant_cents` sur chaque matière, à parts égales
    en division entière — le reste en centimes va à la première matière
    (triée par id) pour que la somme retombe exactement sur le forfait."""
    ids_tries = sorted(matiere_ids)
    nombre = len(ids_tries)
    part = tarif_pack.montant_cents // nombre
    reste = tarif_pack.montant_cents - part * nombre
    return {
        matiere_id: part + (reste if index == 0 else 0)
        for index, matiere_id in enumerate(ids_tries)
    }


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
        self._tarifs_pack = TarifPackRepository(session)
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

        # PACK : « toutes les matières du niveau » = toutes celles qui ont un
        # tarif_eleve défini pour ce niveau (seul signal de rattachement
        # matière/niveau dans ce modèle) — matiere_ids envoyé par le client
        # est ignoré dans ce mode, voir EleveCreation. Chaque matière reste
        # une inscription réelle, seul le tarif copié dessus est fractionné.
        tarifs_fractionnes: dict[int, int] | None = None
        if donnees.est_pack:
            tarif_pack = await self._tarifs_pack.get_par_cle(annee_active.id, donnees.niveau_code)
            if tarif_pack is None:
                raise RessourceIntrouvable(
                    f"Aucun tarif pack défini pour {donnees.niveau_code} pour l'année "
                    f"{annee_active.libelle} — définissez-le dans le référentiel avant "
                    "d'inscrire un élève en pack."
                )
            tarifs_niveau = await self._tarifs_eleve.lister_par_niveau(
                annee_active.id, donnees.niveau_code
            )
            if not tarifs_niveau:
                raise RessourceIntrouvable(
                    f"Aucune matière tarifée pour {donnees.niveau_code} — impossible de "
                    "composer un pack."
                )
            matiere_ids = [t.matiere_id for t in tarifs_niveau]
            tarifs_fractionnes = _fractionner_tarif_pack(tarif_pack, matiere_ids)
        else:
            matiere_ids = donnees.matiere_ids

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
                est_pack=donnees.est_pack,
                reduction_mensuelle_cents=donnees.reduction_mensuelle_cents,
                cree_par=utilisateur_id,
            )
        )

        inscriptions = []
        for matiere_id in matiere_ids:
            if await self._matieres.get_by_id(matiere_id) is None:
                raise RessourceIntrouvable(f"Matière {matiere_id} introuvable.")

            if tarifs_fractionnes is not None:
                tarif_cents = tarifs_fractionnes[matiere_id]
            else:
                tarif = await self._tarifs_eleve.get_par_cle(
                    annee_active.id, donnees.niveau_code, matiere_id
                )
                if tarif is None:
                    raise RessourceIntrouvable(
                        f"Aucun tarif défini pour la matière {matiere_id} en "
                        f"{donnees.niveau_code} pour l'année {annee_active.libelle} — "
                        "définissez-le dans le référentiel avant d'inscrire un élève."
                    )
                tarif_cents = tarif.montant_cents

            inscriptions.append(
                await self._inscriptions.creer(
                    InscriptionMatiere(
                        eleve_id=eleve.id,
                        matiere_id=matiere_id,
                        tarif_mensuel_cents=tarif_cents,
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

    async def definir_pack(
        self,
        eleve_id: int,
        donnees: DefinirPack,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> tuple[Eleve, list[InscriptionMatiere], FraisInscription | None]:
        """Active ou désactive le pack. Activer clôture les inscriptions en
        cours et en recrée une par matière tarifée du niveau, au tarif pack
        fractionné. Désactiver clôture les 6 inscriptions sans en recréer —
        une nouvelle inscription individuelle est un acte séparé ensuite."""
        eleve = await self._eleves.get_by_id(eleve_id)
        if eleve is None:
            raise RessourceIntrouvable(f"Élève {eleve_id} introuvable.")

        if donnees.actif == eleve.est_pack:
            return (
                eleve,
                await self._inscriptions.lister_par_eleve(eleve_id),
                await self._frais.get_by_eleve(eleve_id),
            )

        if donnees.actif and eleve.reduction_mensuelle_cents is not None:
            raise ConflitMetier(
                "Cet élève a une réduction active — désactivez-la avant d'activer le pack."
            )

        aujourdhui = datetime.now(FUSEAU_HORAIRE_CENTRE).date()
        inscriptions_en_cours = [
            i for i in await self._inscriptions.lister_par_eleve(eleve_id) if i.date_fin is None
        ]

        nouvelles_inscriptions: list[InscriptionMatiere] = []
        if donnees.actif:
            tarif_pack = await self._tarifs_pack.get_par_cle(
                eleve.annee_scolaire_id, eleve.niveau_code
            )
            if tarif_pack is None:
                raise RessourceIntrouvable(
                    f"Aucun tarif pack défini pour {eleve.niveau_code} — définissez-le dans le "
                    "référentiel avant d'activer le pack."
                )
            tarifs_niveau = await self._tarifs_eleve.lister_par_niveau(
                eleve.annee_scolaire_id, eleve.niveau_code
            )
            if not tarifs_niveau:
                raise RessourceIntrouvable(
                    f"Aucune matière tarifée pour {eleve.niveau_code} — impossible de composer "
                    "un pack."
                )
            matiere_ids = [t.matiere_id for t in tarifs_niveau]
            tarifs_fractionnes = _fractionner_tarif_pack(tarif_pack, matiere_ids)

            for inscription in inscriptions_en_cours:
                # max(...) : une inscription qui débute dans le futur ne peut
                # pas être close avant sa propre date de début (ck_insc_dates).
                inscription.date_fin = max(aujourdhui, inscription.date_debut)

            for matiere_id in matiere_ids:
                nouvelles_inscriptions.append(
                    await self._inscriptions.creer(
                        InscriptionMatiere(
                            eleve_id=eleve.id,
                            matiere_id=matiere_id,
                            tarif_mensuel_cents=tarifs_fractionnes[matiere_id],
                            date_debut=aujourdhui,
                            cree_par=utilisateur_id,
                        )
                    )
                )
        else:
            for inscription in inscriptions_en_cours:
                inscription.date_fin = max(aujourdhui, inscription.date_debut)

        ancien_est_pack = eleve.est_pack
        eleve.est_pack = donnees.actif

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="eleve",
            entite_id=eleve.id,
            utilisateur_id=utilisateur_id,
            avant={"est_pack": ancien_est_pack},
            apres={"est_pack": donnees.actif},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return (
            eleve,
            await self._inscriptions.lister_par_eleve(eleve_id),
            await self._frais.get_by_eleve(eleve_id),
        )

    async def definir_reduction(
        self,
        eleve_id: int,
        donnees: DefinirReduction,
        utilisateur_id: int,
        adresse_ip: str | None,
    ) -> Eleve:
        """N'affecte AUCUNE inscription — seul le calcul de l'échéance change
        (voir PaiementService.generer_echeances). Les matières suivies
        restent celles déjà inscrites, utilisées normalement pour la paie."""
        eleve = await self._eleves.get_by_id(eleve_id)
        if eleve is None:
            raise RessourceIntrouvable(f"Élève {eleve_id} introuvable.")

        if donnees.actif and eleve.est_pack:
            raise ConflitMetier(
                "Cet élève est en pack — désactivez le pack avant d'activer une réduction."
            )

        ancien = eleve.reduction_mensuelle_cents
        eleve.reduction_mensuelle_cents = donnees.montant_cents if donnees.actif else None

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="eleve",
            entite_id=eleve.id,
            utilisateur_id=utilisateur_id,
            avant={"reduction_mensuelle_cents": ancien},
            apres={"reduction_mensuelle_cents": eleve.reduction_mensuelle_cents},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
        return eleve
