"""Seed initial : niveaux, matières, paramètres, administrateur.

Niveaux/matières/paramètres sont idempotents — relancer `make seed` n'insère
que ce qui manque, ne touche jamais une ligne déjà présente (une valeur de
paramètre modifiée par un admin ne doit pas revenir à sa valeur par défaut).

Email et mot de passe de l'administrateur lus depuis l'environnement
(`ADMIN_INITIAL_EMAIL`, `ADMIN_INITIAL_PASSWORD`), jamais en dur.

Chaque fonction de seed reçoit une `AsyncSession` en paramètre plutôt que de
construire elle-même `FabriqueSession` (qui pointe sur la base de
développement, `POSTGRES_*` de l'environnement réel) : un test qui appellerait
un jour ces fonctions directement écrirait sinon dans `gep`, que le TRUNCATE
des fixtures e2e viderait à la fin du test. `FabriqueSession` n'est construite
que dans le bloc `__main__`, jamais importée ailleurs.
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hacher_mot_de_passe
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.auth.repository import UtilisateurRepository
from app.modules.referentiel.models import Matiere, Niveau, Parametre
from app.modules.referentiel.repository import (
    MatiereRepository,
    NiveauRepository,
    ParametreRepository,
)

# (code, libellé, ordre) — §2 du cahier des charges.
NIVEAUX = [
    ("1AC", "1ère année collège", 1),
    ("2AC", "2ème année collège", 2),
    ("3AC", "3ème année collège", 3),
    ("TC", "Tronc commun", 4),
    ("1BAC", "1ère année baccalauréat", 5),
    ("2BAC", "2ème année baccalauréat", 6),
]

# (code, libellé) — §3.2 du cahier des charges.
MATIERES = [
    ("MATH", "Mathématiques"),
    ("PHYSIQUE_CHIMIE", "Physique-Chimie"),
    ("FRANCAIS", "Français"),
    ("ANGLAIS", "Anglais"),
    ("ARABE", "Arabe"),
    ("SVT", "SVT"),
]

# (clé, valeur, type_valeur, description) — §1 de docs/02-modele-donnees.md.
PARAMETRES = [
    (
        "frais_inscription_cents",
        "5000",
        "entier",
        "Frais d'inscription en centimes (50 DH)",
    ),
    (
        "base_calcul_paie",
        "inscrits",
        "texte",
        "inscrits | payants — voir décision D4",
    ),
    ("nom_centre", "Centre", "texte", "Affiché sur les reçus et rapports"),
]


async def seed_niveaux(session: AsyncSession) -> None:
    repository = NiveauRepository(session)
    crees = 0
    for code, libelle, ordre in NIVEAUX:
        if await repository.existe(code):
            continue
        session.add(Niveau(code=code, libelle=libelle, ordre=ordre))
        crees += 1
    await session.commit()
    print(f"Niveaux : {crees} créé(s), {len(NIVEAUX) - crees} déjà présent(s).")


async def seed_matieres(session: AsyncSession) -> None:
    repository = MatiereRepository(session)
    crees = 0
    for code, libelle in MATIERES:
        if await repository.get_by_code(code) is not None:
            continue
        await repository.creer(Matiere(code=code, libelle=libelle))
        crees += 1
    await session.commit()
    print(f"Matières : {crees} créée(s), {len(MATIERES) - crees} déjà présente(s).")


async def seed_parametres(session: AsyncSession) -> None:
    repository = ParametreRepository(session)
    crees = 0
    for cle, valeur, type_valeur, description in PARAMETRES:
        if await repository.get_by_cle(cle) is not None:
            continue
        await repository.creer(
            Parametre(cle=cle, valeur=valeur, type_valeur=type_valeur, description=description)
        )
        crees += 1
    await session.commit()
    print(f"Paramètres : {crees} créé(s), {len(PARAMETRES) - crees} déjà présent(s).")


async def seed_administrateur_initial(session: AsyncSession) -> None:
    email = os.environ.get("ADMIN_INITIAL_EMAIL")
    mot_de_passe = os.environ.get("ADMIN_INITIAL_PASSWORD")

    if not email or not mot_de_passe:
        print(
            "ADMIN_INITIAL_EMAIL et ADMIN_INITIAL_PASSWORD doivent être définis "
            "dans l'environnement avant de lancer `make seed`.",
            file=sys.stderr,
        )
        sys.exit(1)

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


async def seed_tout(session: AsyncSession) -> None:
    await seed_niveaux(session)
    await seed_matieres(session)
    await seed_parametres(session)
    await seed_administrateur_initial(session)


async def _main() -> None:
    from app.db.session import FabriqueSession

    async with FabriqueSession() as session:
        await seed_tout(session)


if __name__ == "__main__":
    asyncio.run(_main())
