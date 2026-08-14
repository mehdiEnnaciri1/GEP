"""Construction d'utilisateurs de test avec un mot de passe connu en clair."""

from __future__ import annotations

from app.core.security import hacher_mot_de_passe
from app.modules.auth.models import RoleUtilisateur, Utilisateur

MOT_DE_PASSE_TEST = "mot-de-passe-de-test-1234"


def construire_utilisateur(
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
    # La table `professeur` n'existe pas encore (étape 5) donc pas de FK à
    # respecter ici — n'importe quel entier convient pour les tests.
    if professeur_id is None and role == RoleUtilisateur.PROFESSEUR:
        professeur_id = 1

    return Utilisateur(
        nom=nom,
        prenom=prenom,
        email=email,
        mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
        role=role,
        actif=actif,
        professeur_id=professeur_id,
    )
