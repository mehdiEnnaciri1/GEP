"""Tests e2e du référentiel — CRUD années/matières/paramètres, grille de
tarifs, permissions par rôle (§6.6 : ADMIN complet, CAISSIER lecture seule,
PROFESSEUR rien)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from app.modules.referentiel.models import Matiere, Niveau, Parametre
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur

ANNEE_2025_2026 = {
    "libelle": "2025-2026",
    "date_debut": "2025-09-01",
    "date_fin": "2026-06-30",
}


async def _jeton(
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


async def _creer_niveau_et_matiere(session: AsyncSession) -> tuple[str, int]:
    niveau = Niveau(code="1BAC", libelle="1ère année baccalauréat", ordre=5)
    matiere = Matiere(code="MATH", libelle="Mathématiques")
    session.add_all([niveau, matiere])
    await session.commit()
    await session.refresh(matiere)
    return niveau.code, matiere.id


class TestAnneesScolaires:
    async def test_admin_cree_une_annee(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin1@test.ma")
        reponse = await client.post(
            "/api/referentiel/annees-scolaires",
            json=ANNEE_2025_2026,
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 201
        assert reponse.json()["libelle"] == "2025-2026"
        assert reponse.json()["est_active"] is False

    async def test_caissier_ne_peut_pas_creer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        reponse = await client.post(
            "/api/referentiel/annees-scolaires",
            json=ANNEE_2025_2026,
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 403

    async def test_professeur_ne_peut_pas_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )
        reponse = await client.get(
            "/api/referentiel/annees-scolaires", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert reponse.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.get("/api/referentiel/annees-scolaires")
        assert reponse.status_code == 401

    async def test_libelle_duplique_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin2@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await client.post(
            "/api/referentiel/annees-scolaires", json=ANNEE_2025_2026, headers=headers
        )
        rep = await client.post(
            "/api/referentiel/annees-scolaires", json=ANNEE_2025_2026, headers=headers
        )
        assert rep.status_code == 409

    async def test_activer_desactive_les_autres(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        r1 = await client.post(
            "/api/referentiel/annees-scolaires",
            json={"libelle": "2024-2025", "date_debut": "2024-09-01", "date_fin": "2025-06-30"},
            headers=headers,
        )
        r2 = await client.post(
            "/api/referentiel/annees-scolaires", json=ANNEE_2025_2026, headers=headers
        )
        id1, id2 = r1.json()["id"], r2.json()["id"]

        rep_activation_1 = await client.post(
            f"/api/referentiel/annees-scolaires/{id1}/activer", headers=headers
        )
        assert rep_activation_1.json()["est_active"] is True

        rep_activation_2 = await client.post(
            f"/api/referentiel/annees-scolaires/{id2}/activer", headers=headers
        )
        assert rep_activation_2.status_code == 200
        assert rep_activation_2.json()["est_active"] is True

        annees = (await client.get("/api/referentiel/annees-scolaires", headers=headers)).json()
        actives = [a for a in annees if a["est_active"]]
        assert len(actives) == 1
        assert actives[0]["id"] == id2

    async def test_activer_annee_inexistante(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin4@test.ma")
        rep = await client.post(
            "/api/referentiel/annees-scolaires/999999/activer",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 404


class TestMatieres:
    async def test_admin_cree_une_matiere(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin5@test.ma")
        rep = await client.post(
            "/api/referentiel/matieres",
            json={"code": "MATH", "libelle": "Mathématiques"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 201

    async def test_code_duplique_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin6@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await client.post(
            "/api/referentiel/matieres", json={"code": "SVT", "libelle": "SVT"}, headers=headers
        )
        rep = await client.post(
            "/api/referentiel/matieres", json={"code": "SVT", "libelle": "Autre"}, headers=headers
        )
        assert rep.status_code == 409

    async def test_caissier_ne_peut_pas_creer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.post(
            "/api/referentiel/matieres",
            json={"code": "ANGLAIS", "libelle": "Anglais"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_caissier_peut_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.get(
            "/api/referentiel/matieres", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 200


class TestParametres:
    async def test_mise_a_jour_type_entier_invalide(
        self, client: AsyncClient, session: AsyncSession
    ):
        session.add(Parametre(cle="frais_inscription_cents", valeur="5000", type_valeur="entier"))
        await session.commit()

        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin7@test.ma")
        rep = await client.patch(
            "/api/referentiel/parametres/frais_inscription_cents",
            json={"valeur": "pas-un-entier"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 422

    async def test_mise_a_jour_valide(self, client: AsyncClient, session: AsyncSession):
        session.add(Parametre(cle="frais_inscription_cents", valeur="5000", type_valeur="entier"))
        await session.commit()

        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin8@test.ma")
        rep = await client.patch(
            "/api/referentiel/parametres/frais_inscription_cents",
            json={"valeur": "6000"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 200
        assert rep.json()["valeur"] == "6000"

    async def test_caissier_ne_peut_pas_modifier(self, client: AsyncClient, session: AsyncSession):
        session.add(Parametre(cle="nom_centre", valeur="Centre", type_valeur="texte"))
        await session.commit()

        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier4@test.ma"
        )
        rep = await client.patch(
            "/api/referentiel/parametres/nom_centre",
            json={"valeur": "Autre nom"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403


class TestTarifsEleve:
    async def test_admin_definit_puis_met_a_jour_sans_dupliquer(
        self, client: AsyncClient, session: AsyncSession
    ):
        niveau_code, matiere_id = await _creer_niveau_et_matiere(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin9@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        annee_id = (
            await client.post(
                "/api/referentiel/annees-scolaires", json=ANNEE_2025_2026, headers=headers
            )
        ).json()["id"]

        rep1 = await client.put(
            "/api/referentiel/tarifs-eleve",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_cents": 20000,
            },
            headers=headers,
        )
        assert rep1.status_code == 200
        assert rep1.json()["montant_cents"] == 20000

        rep2 = await client.put(
            "/api/referentiel/tarifs-eleve",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_cents": 25000,
            },
            headers=headers,
        )
        assert rep2.status_code == 200
        assert rep2.json()["montant_cents"] == 25000
        assert rep2.json()["id"] == rep1.json()["id"]

        liste = await client.get(
            f"/api/referentiel/tarifs-eleve?annee_scolaire_id={annee_id}", headers=headers
        )
        assert len(liste.json()) == 1

    async def test_caissier_lit_mais_ne_peut_pas_ecrire(
        self, client: AsyncClient, session: AsyncSession
    ):
        niveau_code, matiere_id = await _creer_niveau_et_matiere(session)
        jeton_admin = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin10@test.ma"
        )
        annee_id = (
            await client.post(
                "/api/referentiel/annees-scolaires",
                json=ANNEE_2025_2026,
                headers={"Authorization": f"Bearer {jeton_admin}"},
            )
        ).json()["id"]

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier5@test.ma"
        )
        headers_caissier = {"Authorization": f"Bearer {jeton_caissier}"}

        lecture = await client.get(
            f"/api/referentiel/tarifs-eleve?annee_scolaire_id={annee_id}", headers=headers_caissier
        )
        assert lecture.status_code == 200

        ecriture = await client.put(
            "/api/referentiel/tarifs-eleve",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_cents": 1,
            },
            headers=headers_caissier,
        )
        assert ecriture.status_code == 403

    async def test_annee_inexistante(self, client: AsyncClient, session: AsyncSession):
        niveau_code, matiere_id = await _creer_niveau_et_matiere(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin11@test.ma")
        rep = await client.put(
            "/api/referentiel/tarifs-eleve",
            json={
                "annee_scolaire_id": 999999,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_cents": 100,
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 404


class TestTarifsProfesseur:
    async def test_admin_definit_caissier_ne_peut_pas_ecrire(
        self, client: AsyncClient, session: AsyncSession
    ):
        niveau_code, matiere_id = await _creer_niveau_et_matiere(session)
        jeton_admin = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin12@test.ma"
        )
        headers_admin = {"Authorization": f"Bearer {jeton_admin}"}

        annee_id = (
            await client.post(
                "/api/referentiel/annees-scolaires", json=ANNEE_2025_2026, headers=headers_admin
            )
        ).json()["id"]

        rep = await client.put(
            "/api/referentiel/tarifs-professeur",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_par_eleve_cents": 3500,
            },
            headers=headers_admin,
        )
        assert rep.status_code == 200
        assert rep.json()["montant_par_eleve_cents"] == 3500

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier6@test.ma"
        )
        ecriture = await client.put(
            "/api/referentiel/tarifs-professeur",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_par_eleve_cents": 1,
            },
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert ecriture.status_code == 403

    async def test_lecture_reservee_a_admin(self, client: AsyncClient, session: AsyncSession):
        """Les tarifs professeurs révèlent la marge du centre — contrairement
        aux tarifs élève, le caissier n'y a plus accès du tout, pas même en
        lecture (voir docs/adr/2026-08-16-tarifs-prof-admin-only.md)."""
        jeton_admin = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin13@test.ma"
        )
        annee_id = (
            await client.post(
                "/api/referentiel/annees-scolaires",
                json=ANNEE_2025_2026,
                headers={"Authorization": f"Bearer {jeton_admin}"},
            )
        ).json()["id"]

        lecture_admin = await client.get(
            f"/api/referentiel/tarifs-professeur?annee_scolaire_id={annee_id}",
            headers={"Authorization": f"Bearer {jeton_admin}"},
        )
        assert lecture_admin.status_code == 200

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier7@test.ma"
        )
        lecture_caissier = await client.get(
            f"/api/referentiel/tarifs-professeur?annee_scolaire_id={annee_id}",
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert lecture_caissier.status_code == 403
