"""Construction d'utilisateurs de test avec un mot de passe connu en clair."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hacher_mot_de_passe
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.professeurs.models import Professeur

MOT_DE_PASSE_TEST = "mot-de-passe-de-test-1234"


async def construire_utilisateur(
    session: AsyncSession,
    *,
    email: str,
    role: RoleUtilisateur = RoleUtilisateur.CAISSIER,
    actif: bool = True,
    mot_de_passe: str = MOT_DE_PASSE_TEST,
    nom: str = "Test",
    prenom: str = "Utilisateur",
    professeur_id: int | None = None,
) -> Utilisateur:
    # ck_prof_lie : professeur_id obligatoire si et seulement si role=PROFESSEUR.
    # Depuis l'étape 5, professeur_id porte une vraie ForeignKey — il faut donc
    # une ligne `professeur` existante, pas un entier arbitraire.
    if professeur_id is None and role == RoleUtilisateur.PROFESSEUR:
        professeur = Professeur(nom=nom, prenom=prenom, telephone="0600000000")
        session.add(professeur)
        await session.flush()
        professeur_id = professeur.id

    return Utilisateur(
        nom=nom,
        prenom=prenom,
        email=email,
        mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
        role=role,
        actif=actif,
        professeur_id=professeur_id,
    )
