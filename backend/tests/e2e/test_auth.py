"""Tests e2e du module auth — endpoints via httpx, sur une vraie base (voir
conftest.py). Chaque endpoint protégé a son test 401 (sans jeton) ; les
endpoints réservés à un rôle ont en plus leur test 403 (mauvais rôle)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import JournalAudit
from app.modules.auth.models import RoleUtilisateur
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur


async def _creer_et_connecter(
    client: AsyncClient, session: AsyncSession, *, role: RoleUtilisateur, email: str
) -> str:
    utilisateur = construire_utilisateur(email=email, role=role)
    session.add(utilisateur)
    await session.commit()

    reponse = await client.post(
        "/api/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE_TEST}
    )
    assert reponse.status_code == 200
    return str(reponse.json()["access_token"])


class TestLogin:
    async def test_identifiants_valides(self, client: AsyncClient, session: AsyncSession):
        utilisateur = construire_utilisateur(email="admin@test.ma", role=RoleUtilisateur.ADMIN)
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
        utilisateur = construire_utilisateur(email="admin2@test.ma")
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
        utilisateur = construire_utilisateur(email="inactif@test.ma", actif=False)
        session.add(utilisateur)
        await session.commit()

        reponse = await client.post(
            "/api/auth/login",
            json={"email": "inactif@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST},
        )

        assert reponse.status_code == 401

    async def test_connexion_reussie_journalisee(self, client: AsyncClient, session: AsyncSession):
        utilisateur = construire_utilisateur(email="journal@test.ma")
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
        utilisateur = construire_utilisateur(email="echec@test.ma")
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

        reponse = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {jeton}"}
        )

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
        utilisateur = construire_utilisateur(email="refresh@test.ma")
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
