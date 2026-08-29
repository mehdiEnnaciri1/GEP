"""Services du référentiel — frontière transactionnelle. Chaque méthode
commite elle-même son unité de travail (voir §Couches de CLAUDE.md)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitMetier, RessourceIntrouvable, ValidationMetier
from app.modules.referentiel.models import (
    AnneeScolaire,
    Matiere,
    Niveau,
    Parametre,
    TarifEleve,
    TarifPack,
    TarifProfesseur,
)
from app.modules.referentiel.repository import (
    AnneeScolaireRepository,
    MatiereRepository,
    NiveauRepository,
    ParametreRepository,
    TarifEleveRepository,
    TarifPackRepository,
    TarifProfesseurRepository,
)
from app.modules.referentiel.schemas import (
    AnneeScolaireCreation,
    AnneeScolaireMiseAJour,
    MatiereCreation,
    MatiereMiseAJour,
)


class AnneeScolaireService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._annees = AnneeScolaireRepository(session)

    async def lister(self) -> list[AnneeScolaire]:
        return await self._annees.lister()

    async def creer(self, donnees: AnneeScolaireCreation) -> AnneeScolaire:
        if await self._annees.get_by_libelle(donnees.libelle) is not None:
            raise ConflitMetier(f"Une année scolaire {donnees.libelle} existe déjà.")

        annee = await self._annees.creer(
            AnneeScolaire(
                libelle=donnees.libelle,
                date_debut=donnees.date_debut,
                date_fin=donnees.date_fin,
            )
        )
        await self._session.commit()
        return annee

    async def mettre_a_jour(self, annee_id: int, donnees: AnneeScolaireMiseAJour) -> AnneeScolaire:
        annee = await self._annees.get_by_id(annee_id)
        if annee is None:
            raise RessourceIntrouvable(f"Année scolaire {annee_id} introuvable.")

        for champ, valeur in donnees.model_dump(exclude_unset=True).items():
            setattr(annee, champ, valeur)

        await self._session.commit()
        return annee

    async def activer(self, annee_id: int) -> AnneeScolaire:
        """Désactive toutes les années puis active celle-ci, dans la même
        transaction — sinon l'index unique partiel sur `est_active` (une
        seule année active à la fois, voir décision D5) fait échouer
        l'opération dès qu'une autre année est déjà active."""

        annee = await self._annees.get_by_id(annee_id)
        if annee is None:
            raise RessourceIntrouvable(f"Année scolaire {annee_id} introuvable.")

        await self._annees.desactiver_toutes()
        annee.est_active = True
        await self._session.commit()
        return annee


class NiveauService:
    def __init__(self, session: AsyncSession) -> None:
        self._niveaux = NiveauRepository(session)

    async def lister(self) -> list[Niveau]:
        return await self._niveaux.lister()


class MatiereService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._matieres = MatiereRepository(session)

    async def lister(self) -> list[Matiere]:
        return await self._matieres.lister()

    async def creer(self, donnees: MatiereCreation) -> Matiere:
        if await self._matieres.get_by_code(donnees.code) is not None:
            raise ConflitMetier(f"La matière {donnees.code} existe déjà.")

        matiere = await self._matieres.creer(Matiere(code=donnees.code, libelle=donnees.libelle))
        await self._session.commit()
        return matiere

    async def mettre_a_jour(self, matiere_id: int, donnees: MatiereMiseAJour) -> Matiere:
        matiere = await self._matieres.get_by_id(matiere_id)
        if matiere is None:
            raise RessourceIntrouvable(f"Matière {matiere_id} introuvable.")

        for champ, valeur in donnees.model_dump(exclude_unset=True).items():
            setattr(matiere, champ, valeur)

        await self._session.commit()
        return matiere


class ParametreService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._parametres = ParametreRepository(session)

    async def lister(self) -> list[Parametre]:
        return await self._parametres.lister()

    async def mettre_a_jour(self, cle: str, valeur: str) -> Parametre:
        parametre = await self._parametres.get_by_cle(cle)
        if parametre is None:
            raise RessourceIntrouvable(f"Paramètre {cle} introuvable.")

        if parametre.type_valeur == "entier" and not valeur.lstrip("-").isdigit():
            raise ValidationMetier(f"La valeur de {cle} doit être un entier, reçu : {valeur!r}.")
        if parametre.type_valeur == "booleen" and valeur not in ("true", "false"):
            raise ValidationMetier(f"La valeur de {cle} doit être 'true' ou 'false'.")

        parametre.valeur = valeur
        await self._session.commit()
        return parametre


class TarifService:
    """Regroupe tarif_eleve et tarif_professeur : même clé (année, niveau,
    matière), même logique d'upsert, deux tables distinctes (voir models.py)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._annees = AnneeScolaireRepository(session)
        self._niveaux = NiveauRepository(session)
        self._matieres = MatiereRepository(session)
        self._tarifs_eleve = TarifEleveRepository(session)
        self._tarifs_pack = TarifPackRepository(session)
        self._tarifs_professeur = TarifProfesseurRepository(session)

    async def _verifier_cle(
        self, annee_scolaire_id: int, niveau_code: str, matiere_id: int
    ) -> None:
        await self._verifier_cle_niveau(annee_scolaire_id, niveau_code)
        if await self._matieres.get_by_id(matiere_id) is None:
            raise RessourceIntrouvable(f"Matière {matiere_id} introuvable.")

    async def _verifier_cle_niveau(self, annee_scolaire_id: int, niveau_code: str) -> None:
        if await self._annees.get_by_id(annee_scolaire_id) is None:
            raise RessourceIntrouvable(f"Année scolaire {annee_scolaire_id} introuvable.")
        if not await self._niveaux.existe(niveau_code):
            raise RessourceIntrouvable(f"Niveau {niveau_code} introuvable.")

    async def lister_tarifs_eleve(self, annee_scolaire_id: int) -> list[TarifEleve]:
        return await self._tarifs_eleve.lister_par_annee(annee_scolaire_id)

    async def definir_tarif_eleve(
        self, annee_scolaire_id: int, niveau_code: str, matiere_id: int, montant_cents: int
    ) -> TarifEleve:
        await self._verifier_cle(annee_scolaire_id, niveau_code, matiere_id)

        tarif = await self._tarifs_eleve.get_par_cle(annee_scolaire_id, niveau_code, matiere_id)
        if tarif is None:
            tarif = await self._tarifs_eleve.creer(
                TarifEleve(
                    annee_scolaire_id=annee_scolaire_id,
                    niveau_code=niveau_code,
                    matiere_id=matiere_id,
                    montant_cents=montant_cents,
                )
            )
        else:
            tarif.montant_cents = montant_cents

        await self._session.commit()
        return tarif

    async def lister_tarifs_professeur(self, annee_scolaire_id: int) -> list[TarifProfesseur]:
        return await self._tarifs_professeur.lister_par_annee(annee_scolaire_id)

    async def definir_tarif_professeur(
        self,
        annee_scolaire_id: int,
        niveau_code: str,
        matiere_id: int,
        montant_par_eleve_cents: int,
    ) -> TarifProfesseur:
        await self._verifier_cle(annee_scolaire_id, niveau_code, matiere_id)

        tarif = await self._tarifs_professeur.get_par_cle(
            annee_scolaire_id, niveau_code, matiere_id
        )
        if tarif is None:
            tarif = await self._tarifs_professeur.creer(
                TarifProfesseur(
                    annee_scolaire_id=annee_scolaire_id,
                    niveau_code=niveau_code,
                    matiere_id=matiere_id,
                    montant_par_eleve_cents=montant_par_eleve_cents,
                )
            )
        else:
            tarif.montant_par_eleve_cents = montant_par_eleve_cents

        await self._session.commit()
        return tarif

    async def lister_tarifs_pack(self, annee_scolaire_id: int) -> list[TarifPack]:
        return await self._tarifs_pack.lister_par_annee(annee_scolaire_id)

    async def definir_tarif_pack(
        self, annee_scolaire_id: int, niveau_code: str, montant_cents: int
    ) -> TarifPack:
        await self._verifier_cle_niveau(annee_scolaire_id, niveau_code)

        tarif = await self._tarifs_pack.get_par_cle(annee_scolaire_id, niveau_code)
        if tarif is None:
            tarif = await self._tarifs_pack.creer(
                TarifPack(
                    annee_scolaire_id=annee_scolaire_id,
                    niveau_code=niveau_code,
                    montant_cents=montant_cents,
                )
            )
        else:
            tarif.montant_cents = montant_cents

        await self._session.commit()
        return tarif
