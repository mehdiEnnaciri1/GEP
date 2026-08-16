"""Tests e2e du module auth — endpoints via httpx, sur une vraie base (voir
conftest.py). Chaque endpoint protégé a son test 401 (sans jeton) ; les
endpoints réservés à un rôle ont en plus leur test 403 (mauvais rôle)."""

from __future__ import annotations

import asyncio

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import JournalAudit
from app.modules.auth.models import RoleUtilisateur
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur


async def _creer_et_connecter(
    client: AsyncClient, session: AsyncSession, *, role: RoleUtilisateur, email: str
) -> str:
    utilisateur = await construire_utilisateur(session, email=email, role=role)
    session.add(utilisateur)
    await session.commit()

    reponse = await client.post(
        "/api/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE_TEST}
    )
    assert reponse.status_code == 200
    return str(reponse.json()["access_token"])


class TestLogin:
    async def test_identifiants_valides(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(
            session, email="admin@test.ma", role=RoleUtilisateur.ADMIN
        )
        session.add(utilisateur)
        await session.commit()

        reponse = await client.post(
            "/api/auth/login",
            json={"email": "admin@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        assert reponse.status_code == 200
        corps = reponse.json()
        assert corps["utilisateur"]["email"] == "admin@test.ma"
        assert corps["utilisateur"]["role"] == "ADMIN"
        assert "mot_de_passe_hash" not in corps["utilisateur"]
        assert "refresh_token" in reponse.cookies

    async def test_mauvais_mot_de_passe(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(session, email="admin2@test.ma")
        session.add(utilisateur)
        await session.commit()

        reponse = await client.post(
            "/api/auth/login",
            json={"email": "admin2@test.ma", "mot_de_passe": "mauvais-mot-de-passe"},
        )

        assert reponse.status_code == 401

    async def test_email_inexistant(self, client: AsyncClient):
        reponse = await client.post(
            "/api/auth/login",
            json={"email": "personne@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        assert reponse.status_code == 401

    async def test_utilisateur_inactif(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(session, email="inactif@test.ma", actif=False)
        session.add(utilisateur)
        await session.commit()

        reponse = await client.post(
            "/api/auth/login",
            json={"email": "inactif@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        assert reponse.status_code == 401

    async def test_connexion_reussie_journalisee(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(session, email="journal@test.ma")
        session.add(utilisateur)
        await session.commit()

        await client.post(
            "/api/auth/login",
            json={"email": "journal@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        entrees = (
            (await session.execute(select(JournalAudit).where(JournalAudit.action == "CONNEXION")))
            .scalars()
            .all()
        )
        assert len(entrees) == 1
        assert entrees[0].entite == "utilisateur"

    async def test_connexion_echouee_journalisee(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(session, email="echec@test.ma")
        session.add(utilisateur)
        await session.commit()

        await client.post(
            "/api/auth/login",
            json={"email": "echec@test.ma", "mot_de_passe": "faux"},
        )

        entrees = (
            (
                await session.execute(
                    select(JournalAudit).where(JournalAudit.action == "CONNEXION_ECHOUEE")
                )
            )
            .scalars()
            .all()
        )
        assert len(entrees) == 1


class TestMe:
    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.get("/api/auth/me")
        assert reponse.status_code == 401

    async def test_avec_jeton_valide(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.CAISSIER, email="me@test.ma"
        )

        reponse = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {jeton}"})

        assert reponse.status_code == 200
        assert reponse.json()["email"] == "me@test.ma"

    async def test_jeton_invalide(self, client: AsyncClient):
        reponse = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer ceci-nest-pas-un-jwt"}
        )
        assert reponse.status_code == 401


class TestRefresh:
    async def test_sans_cookie(self, client: AsyncClient):
        reponse = await client.post("/api/auth/refresh")
        assert reponse.status_code == 401

    async def test_avec_cookie_valide(self, client: AsyncClient, session: AsyncSession):
        utilisateur = await construire_utilisateur(session, email="refresh@test.ma")
        session.add(utilisateur)
        await session.commit()

        await client.post(
            "/api/auth/login",
            json={"email": "refresh@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        reponse = await client.post("/api/auth/refresh")

        assert reponse.status_code == 200
        assert "access_token" in reponse.json()


class TestLogout:
    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.post("/api/auth/logout")
        assert reponse.status_code == 401

    async def test_avec_jeton_valide(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.CAISSIER, email="logout@test.ma"
        )

        reponse = await client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {jeton}"}
        )

        assert reponse.status_code == 204
        assert "refresh_token" not in reponse.cookies

    async def test_refresh_token_revoque_apres_logout(
        self, client: AsyncClient, session: AsyncSession
    ):
        """La dette de l'étape 1 : un refresh token émis avant le logout ne
        doit plus jamais fonctionner, même s'il n'est pas encore expiré —
        typiquement un jeton volé ou mis en cache dans un autre onglet."""
        utilisateur = await construire_utilisateur(session, email="revoc1@test.ma")
        session.add(utilisateur)
        await session.commit()

        login = await client.post(
            "/api/auth/login",
            json={"email": "revoc1@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )
        ancien_refresh_token = login.cookies["refresh_token"]
        access_token = login.json()["access_token"]

        deconnexion = await client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert deconnexion.status_code == 204

        # logout a supprimé le cookie du client : on simule un jeton
        # volé/mis en cache en le reposant explicitement sur le client.
        client.cookies.set("refresh_token", ancien_refresh_token)
        reponse = await client.post("/api/auth/refresh")
        assert reponse.status_code == 401

    async def test_nouvelle_connexion_apres_logout_fonctionne(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Non-régression : la révocation ne doit pas bloquer une connexion
        FUTURE, seulement les jetons émis AVANT le logout.

        `iat` est un entier de secondes (imposé par la norme JWT), alors que
        `tokens_invalides_avant` est stocké avec une précision microseconde.
        Si la seconde connexion tombait dans la MÊME seconde que le logout,
        son `iat` tronqué pourrait se retrouver antérieur à
        `tokens_invalides_avant` et être rejeté à tort — une limitation
        connue de toute révocation par timestamp à la seconde près. On force
        ici un écart de plus d'une seconde pour ne pas tester une course
        d'arrondi plutôt que le comportement réel."""
        utilisateur = await construire_utilisateur(session, email="revoc2@test.ma")
        session.add(utilisateur)
        await session.commit()

        premiere_connexion = await client.post(
            "/api/auth/login",
            json={"email": "revoc2@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )
        access_token = premiere_connexion.json()["access_token"]
        await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"})

        await asyncio.sleep(1.1)

        seconde_connexion = await client.post(
            "/api/auth/login",
            json={"email": "revoc2@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )
        assert seconde_connexion.status_code == 200

        reponse = await client.post("/api/auth/refresh")
        assert reponse.status_code == 200
        assert "access_token" in reponse.json()


class TestDeconnecterPartout:
    async def test_admin_revoque_un_autre_utilisateur(
        self, client: AsyncClient, session: AsyncSession
    ):
        cible = await construire_utilisateur(session, email="cible@test.ma")
        session.add(cible)
        await session.commit()
        await session.refresh(cible)

        connexion_cible = await client.post(
            "/api/auth/login", json={"email": "cible@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST}
        )
        refresh_token_cible = connexion_cible.cookies["refresh_token"]

        jeton_admin = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.ADMIN, email="admin-revoc@test.ma"
        )
        rep = await client.post(
            "/api/admin/deconnecter-partout",
            json={"utilisateur_id": cible.id},
            headers={"Authorization": f"Bearer {jeton_admin}"},
        )
        assert rep.status_code == 204

        client.cookies.set("refresh_token", refresh_token_cible)
        reponse = await client.post("/api/auth/refresh")
        assert reponse.status_code == 401

    async def test_utilisateur_introuvable(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.ADMIN, email="admin-revoc2@test.ma"
        )
        rep = await client.post(
            "/api/admin/deconnecter-partout",
            json={"utilisateur_id": 999999},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 404

    async def test_caissier_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier-revoc@test.ma"
        )
        rep = await client.post(
            "/api/admin/deconnecter-partout",
            json={"utilisateur_id": 1},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.post("/api/admin/deconnecter-partout", json={"utilisateur_id": 1})
        assert rep.status_code == 401


class TestListerUtilisateursAdminSeulement:
    """L'endpoint qui matérialise §6.6 : « Utilisateurs — Complet (ADMIN) /
    Aucun (CAISSIER, PROFESSEUR) »."""

    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.get("/api/auth/utilisateurs")
        assert reponse.status_code == 401

    async def test_caissier_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier@test.ma"
        )

        reponse = await client.get(
            "/api/auth/utilisateurs", headers={"Authorization": f"Bearer {jeton}"}
        )

        assert reponse.status_code == 403

    async def test_professeur_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof@test.ma"
        )

        reponse = await client.get(
            "/api/auth/utilisateurs", headers={"Authorization": f"Bearer {jeton}"}
        )

        assert reponse.status_code == 403

    async def test_admin_autorise(self, client: AsyncClient, session: AsyncSession):
        jeton = await _creer_et_connecter(
            client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma"
        )

        reponse = await client.get(
            "/api/auth/utilisateurs", headers={"Authorization": f"Bearer {jeton}"}
        )

        assert reponse.status_code == 200
        emails = [u["email"] for u in reponse.json()]
        assert "admin3@test.ma" in emails
