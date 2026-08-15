"""Tests e2e du module professeurs — CRUD professeur, affectations (contrainte
D3 : un seul professeur par couple matière/niveau, message explicite en cas de
conflit), compteur d'élèves par affectation, permissions par rôle (§6.6 :
ADMIN complet, CAISSIER lecture, PROFESSEUR sa fiche)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from tests.factories.professeurs import creer_affectation, creer_professeur
from tests.factories.referentiel import (
    creer_annee_scolaire,
    creer_matiere,
    creer_niveau,
    creer_tarif_eleve,
)
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur


async def _jeton(
    client: AsyncClient,
    session: AsyncSession,
    *,
    role: RoleUtilisateur,
    email: str,
    professeur_id: int | None = None,
) -> str:
    utilisateur = await construire_utilisateur(
        session, email=email, role=role, professeur_id=professeur_id
    )
    session.add(utilisateur)
    await session.commit()

    reponse = await client.post(
        "/api/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE_TEST}
    )
    assert reponse.status_code == 200
    return str(reponse.json()["access_token"])


async def _preparer_referentiel(session: AsyncSession) -> tuple[int, str, int]:
    annee = await creer_annee_scolaire(session)
    niveau = await creer_niveau(session)
    matiere = await creer_matiere(session)
    return annee.id, niveau.code, matiere.id


class TestProfesseurs:
    async def test_admin_cree_un_professeur(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin1@test.ma")
        rep = await client.post(
            "/api/professeurs",
            json={"nom": "Alaoui", "prenom": "Karim", "telephone": "0600000001"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 201
        assert rep.json()["nom"] == "Alaoui"
        assert rep.json()["actif"] is True

    async def test_caissier_ne_peut_pas_creer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        rep = await client.post(
            "/api/professeurs",
            json={"nom": "Alaoui", "prenom": "Karim", "telephone": "0600000001"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_caissier_peut_lister(self, client: AsyncClient, session: AsyncSession):
        await creer_professeur(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.get("/api/professeurs", headers={"Authorization": f"Bearer {jeton}"})
        assert rep.status_code == 200
        assert len(rep.json()) == 1

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get("/api/professeurs")
        assert rep.status_code == 401

    async def test_professeur_ne_peut_pas_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )
        rep = await client.get("/api/professeurs", headers={"Authorization": f"Bearer {jeton}"})
        assert rep.status_code == 403

    async def test_admin_met_a_jour(self, client: AsyncClient, session: AsyncSession):
        professeur = await creer_professeur(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin2@test.ma")
        rep = await client.patch(
            f"/api/professeurs/{professeur.id}",
            json={"actif": False},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 200
        assert rep.json()["actif"] is False

    async def test_professeur_consulte_sa_propre_fiche(
        self, client: AsyncClient, session: AsyncSession
    ):
        professeur = await creer_professeur(session)
        jeton = await _jeton(
            client,
            session,
            role=RoleUtilisateur.PROFESSEUR,
            email="prof2@test.ma",
            professeur_id=professeur.id,
        )
        rep = await client.get("/api/professeurs/me", headers={"Authorization": f"Bearer {jeton}"})
        assert rep.status_code == 200
        assert rep.json()["id"] == professeur.id
        assert rep.json()["affectations"] == []

    async def test_admin_ne_peut_pas_appeler_me(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma")
        rep = await client.get("/api/professeurs/me", headers={"Authorization": f"Bearer {jeton}"})
        assert rep.status_code == 403

    async def test_professeur_introuvable(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin4@test.ma")
        rep = await client.get(
            "/api/professeurs/999999", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 404


class TestAffectations:
    async def test_admin_cree_une_affectation(self, client: AsyncClient, session: AsyncSession):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        professeur = await creer_professeur(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin5@test.ma")

        rep = await client.post(
            "/api/affectations",
            json={
                "professeur_id": professeur.id,
                "matiere_id": matiere_id,
                "niveau_code": niveau_code,
                "annee_scolaire_id": annee_id,
                "date_debut": "2025-09-01",
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 201
        assert rep.json()["nombre_eleves"] == 0

    async def test_caissier_ne_peut_pas_creer_affectation(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        professeur = await creer_professeur(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.post(
            "/api/affectations",
            json={
                "professeur_id": professeur.id,
                "matiere_id": matiere_id,
                "niveau_code": niveau_code,
                "annee_scolaire_id": annee_id,
                "date_debut": "2025-09-01",
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_deuxieme_professeur_meme_couple_refuse_avec_message_explicite(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        premier = await creer_professeur(session, nom="Alaoui", prenom="Karim")
        second = await creer_professeur(session, nom="Bennani", prenom="Yassine")
        await creer_affectation(
            session,
            professeur_id=premier.id,
            matiere_id=matiere_id,
            niveau_code=niveau_code,
            annee_scolaire_id=annee_id,
        )

        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin6@test.ma")
        rep = await client.post(
            "/api/affectations",
            json={
                "professeur_id": second.id,
                "matiere_id": matiere_id,
                "niveau_code": niveau_code,
                "annee_scolaire_id": annee_id,
                "date_debut": "2025-09-01",
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 409
        assert "Karim" in rep.json()["detail"]
        assert "Alaoui" in rep.json()["detail"]

    async def test_professeur_introuvable(self, client: AsyncClient, session: AsyncSession):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin7@test.ma")
        rep = await client.post(
            "/api/affectations",
            json={
                "professeur_id": 999999,
                "matiere_id": matiere_id,
                "niveau_code": niveau_code,
                "annee_scolaire_id": annee_id,
                "date_debut": "2025-09-01",
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 404

    async def test_compteur_eleves_par_affectation(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        await creer_tarif_eleve(
            session, annee_scolaire_id=annee_id, niveau_code=niveau_code, matiere_id=matiere_id
        )
        professeur = await creer_professeur(session)
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_id,
            niveau_code=niveau_code,
            annee_scolaire_id=annee_id,
        )

        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin8@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        for i in range(2):
            await client.post(
                "/api/eleves",
                json={
                    "nom": "Eleve",
                    "prenom": f"Numero{i}",
                    "telephone_parent": "0600000000",
                    "niveau_code": niveau_code,
                    "date_inscription": "2025-09-15",
                    "matiere_ids": [matiere_id],
                },
                headers=headers,
            )

        rep = await client.get(f"/api/affectations?annee_scolaire_id={annee_id}", headers=headers)
        assert rep.status_code == 200
        assert rep.json()[0]["nombre_eleves"] == 2

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get("/api/affectations")
        assert rep.status_code == 401

    async def test_admin_supprime_une_affectation(self, client: AsyncClient, session: AsyncSession):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        professeur = await creer_professeur(session)
        affectation = await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_id,
            niveau_code=niveau_code,
            annee_scolaire_id=annee_id,
        )
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin9@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        rep = await client.delete(f"/api/affectations/{affectation.id}", headers=headers)
        assert rep.status_code == 204

        liste = await client.get(f"/api/affectations?annee_scolaire_id={annee_id}", headers=headers)
        assert liste.json() == []

    async def test_caissier_ne_peut_pas_supprimer(self, client: AsyncClient, session: AsyncSession):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        professeur = await creer_professeur(session)
        affectation = await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_id,
            niveau_code=niveau_code,
            annee_scolaire_id=annee_id,
        )
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier4@test.ma"
        )
        rep = await client.delete(
            f"/api/affectations/{affectation.id}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403
