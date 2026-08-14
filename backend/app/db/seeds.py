"""Seed initial. Étape 1 : uniquement l'administrateur initial — les
référentiels (niveaux, matières, catégories de charges) arrivent à l'étape 2.

Email et mot de passe lus depuis l'environnement (`ADMIN_INITIAL_EMAIL`,
`ADMIN_INITIAL_PASSWORD`), jamais en dur. Exécution : `make seed`.
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.core.security import hacher_mot_de_passe
from app.db.session import FabriqueSession
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.auth.repository import UtilisateurRepository


async def seed_administrateur_initial() -> None:
    email = os.environ.get("ADMIN_INITIAL_EMAIL")
    mot_de_passe = os.environ.get("ADMIN_INITIAL_PASSWORD")

    if not email or not mot_de_passe:
        print(
            "ADMIN_INITIAL_EMAIL et ADMIN_INITIAL_PASSWORD doivent être définis "
            "dans l'environnement avant de lancer `make seed`.",
            file=sys.stderr,
        )
        sys.exit(1)

    async with FabriqueSession() as session:
        repository = UtilisateurRepository(session)

        if await repository.get_by_email(email) is not None:
            print(f"Un utilisateur existe déjà pour {email} — rien à faire.")
            return

        await repository.creer(
            Utilisateur(
                nom="Administrateur",
                prenom="Initial",
                email=email,
                mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe),
                role=RoleUtilisateur.ADMIN,
            )
        )
        await session.commit()
        print(f"Administrateur initial créé : {email}")


if __name__ == "__main__":
    asyncio.run(seed_administrateur_initial())
