"""Endpoints HTTP du référentiel. CRUD réservé à ADMIN, lecture ouverte en
plus à CAISSIER, rien pour PROFESSEUR (voir §6.6 de docs/01-architecture.md).
`niveau` est une table de référence figée par le cahier des charges : lecture
seule, aucun endpoint d'écriture."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.referentiel.schemas import (
    AnneeScolaireCreation,
    AnneeScolaireMiseAJour,
    AnneeScolairePublique,
    MatiereCreation,
    MatiereMiseAJour,
    MatierePublique,
    NiveauPublique,
    ParametreMiseAJour,
    ParametrePublique,
    TarifEleveDefinition,
    TarifElevePublique,
    TarifPackDefinition,
    TarifPackPublique,
    TarifProfesseurDefinition,
    TarifProfesseurPublique,
)
from app.modules.referentiel.service import (
    AnneeScolaireService,
    MatiereService,
    NiveauService,
    ParametreService,
    TarifService,
)

router = APIRouter(prefix="/referentiel", tags=["referentiel"])

_LECTURE = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
_ECRITURE = exige_role(RoleUtilisateur.ADMIN)


# ---- Années scolaires ------------------------------------------------------


@router.get("/annees-scolaires", response_model=list[AnneeScolairePublique])
async def lister_annees_scolaires(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[AnneeScolairePublique]:
    annees = await AnneeScolaireService(session).lister()
    return [AnneeScolairePublique.model_validate(a) for a in annees]


@router.post("/annees-scolaires", response_model=AnneeScolairePublique, status_code=201)
async def creer_annee_scolaire(
    donnees: AnneeScolaireCreation,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> AnneeScolairePublique:
    annee = await AnneeScolaireService(session).creer(donnees)
    return AnneeScolairePublique.model_validate(annee)


@router.patch("/annees-scolaires/{annee_id}", response_model=AnneeScolairePublique)
async def mettre_a_jour_annee_scolaire(
    annee_id: int,
    donnees: AnneeScolaireMiseAJour,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> AnneeScolairePublique:
    annee = await AnneeScolaireService(session).mettre_a_jour(annee_id, donnees)
    return AnneeScolairePublique.model_validate(annee)


@router.post("/annees-scolaires/{annee_id}/activer", response_model=AnneeScolairePublique)
async def activer_annee_scolaire(
    annee_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> AnneeScolairePublique:
    annee = await AnneeScolaireService(session).activer(annee_id)
    return AnneeScolairePublique.model_validate(annee)


# ---- Niveaux (lecture seule) ------------------------------------------------


@router.get("/niveaux", response_model=list[NiveauPublique])
async def lister_niveaux(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[NiveauPublique]:
    niveaux = await NiveauService(session).lister()
    return [NiveauPublique.model_validate(n) for n in niveaux]


# ---- Matières ---------------------------------------------------------------


@router.get("/matieres", response_model=list[MatierePublique])
async def lister_matieres(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[MatierePublique]:
    matieres = await MatiereService(session).lister()
    return [MatierePublique.model_validate(m) for m in matieres]


@router.post("/matieres", response_model=MatierePublique, status_code=201)
async def creer_matiere(
    donnees: MatiereCreation,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> MatierePublique:
    matiere = await MatiereService(session).creer(donnees)
    return MatierePublique.model_validate(matiere)


@router.patch("/matieres/{matiere_id}", response_model=MatierePublique)
async def mettre_a_jour_matiere(
    matiere_id: int,
    donnees: MatiereMiseAJour,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> MatierePublique:
    matiere = await MatiereService(session).mettre_a_jour(matiere_id, donnees)
    return MatierePublique.model_validate(matiere)


# ---- Paramètres ---------------------------------------------------------------


@router.get("/parametres", response_model=list[ParametrePublique])
async def lister_parametres(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[ParametrePublique]:
    parametres = await ParametreService(session).lister()
    return [ParametrePublique.model_validate(p) for p in parametres]


@router.patch("/parametres/{cle}", response_model=ParametrePublique)
async def mettre_a_jour_parametre(
    cle: str,
    donnees: ParametreMiseAJour,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> ParametrePublique:
    parametre = await ParametreService(session).mettre_a_jour(cle, donnees.valeur)
    return ParametrePublique.model_validate(parametre)


# ---- Tarifs élève -------------------------------------------------------------


@router.get("/tarifs-eleve", response_model=list[TarifElevePublique])
async def lister_tarifs_eleve(
    annee_scolaire_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[TarifElevePublique]:
    tarifs = await TarifService(session).lister_tarifs_eleve(annee_scolaire_id)
    return [TarifElevePublique.model_validate(t) for t in tarifs]


@router.put("/tarifs-eleve", response_model=TarifElevePublique)
async def definir_tarif_eleve(
    donnees: TarifEleveDefinition,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> TarifElevePublique:
    tarif = await TarifService(session).definir_tarif_eleve(
        donnees.annee_scolaire_id, donnees.niveau_code, donnees.matiere_id, donnees.montant_cents
    )
    return TarifElevePublique.model_validate(tarif)


# ---- Tarifs pack (forfait toutes matières du niveau) -----------------------


@router.get("/tarifs-pack", response_model=list[TarifPackPublique])
async def lister_tarifs_pack(
    annee_scolaire_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> list[TarifPackPublique]:
    tarifs = await TarifService(session).lister_tarifs_pack(annee_scolaire_id)
    return [TarifPackPublique.model_validate(t) for t in tarifs]


@router.put("/tarifs-pack", response_model=TarifPackPublique)
async def definir_tarif_pack(
    donnees: TarifPackDefinition,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> TarifPackPublique:
    tarif = await TarifService(session).definir_tarif_pack(
        donnees.annee_scolaire_id, donnees.niveau_code, donnees.montant_cents
    )
    return TarifPackPublique.model_validate(tarif)


# ---- Tarifs professeur ---------------------------------------------------------


@router.get("/tarifs-professeur", response_model=list[TarifProfesseurPublique])
async def lister_tarifs_professeur(
    annee_scolaire_id: int,
    session: AsyncSession = Depends(get_session),
    # ADMIN seul : les tarifs professeurs révèlent la marge du centre par
    # matière/niveau, contrairement aux tarifs élève dont le caissier a besoin
    # à la caisse. Voir docs/adr/2026-08-16-tarifs-prof-admin-only.md.
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> list[TarifProfesseurPublique]:
    tarifs = await TarifService(session).lister_tarifs_professeur(annee_scolaire_id)
    return [TarifProfesseurPublique.model_validate(t) for t in tarifs]


@router.put("/tarifs-professeur", response_model=TarifProfesseurPublique)
async def definir_tarif_professeur(
    donnees: TarifProfesseurDefinition,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ECRITURE),
) -> TarifProfesseurPublique:
    tarif = await TarifService(session).definir_tarif_professeur(
        donnees.annee_scolaire_id,
        donnees.niveau_code,
        donnees.matiere_id,
        donnees.montant_par_eleve_cents,
    )
    return TarifProfesseurPublique.model_validate(tarif)
