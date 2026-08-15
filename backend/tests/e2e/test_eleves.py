"""Tests e2e du module eleves — création (matricule, copie du tarif),
recherche/filtres, changement de statut, permissions par rôle.

Le test le plus important de cette étape (D1) : modifier un tarif du
référentiel après l'inscription d'un élève ne doit STRICTEMENT RIEN changer à
son inscription existante — le tarif est copié, jamais référencé.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from tests.factories.referentiel import (
    creer_annee_scolaire,
    creer_matiere,
    creer_niveau,
    creer_tarif_eleve,
)
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur


async def _jeton(
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


async def _preparer_referentiel(session: AsyncSession) -> tuple[int, str, int]:
    """Année active + niveau + matière + tarif défini. Retourne
    (annee_scolaire_id, niveau_code, matiere_id)."""
    annee = await creer_annee_scolaire(session)
    niveau = await creer_niveau(session)
    matiere = await creer_matiere(session)
    await creer_tarif_eleve(
        session,
        annee_scolaire_id=annee.id,
        niveau_code=niveau.code,
        matiere_id=matiere.id,
        montant_cents=20000,
    )
    return annee.id, niveau.code, matiere.id


def _donnees_eleve(niveau_code: str, matiere_id: int) -> dict:
    return {
        "nom": "Alaoui",
        "prenom": "Yassine",
        "telephone_parent": "0600000000",
        "niveau_code": niveau_code,
        "date_inscription": "2025-09-15",
        "matiere_ids": [matiere_id],
    }


class TestCreationEleve:
    async def test_admin_cree_un_eleve_avec_matricule_et_tarif_copie(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin1@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json=_donnees_eleve(niveau_code, matiere_id),
            headers={"Authorization": f"Bearer {jeton}"},
        )

        assert reponse.status_code == 201
        corps = reponse.json()
        assert corps["matricule"] == "E-2025-0001"
        assert corps["annee_scolaire_id"] == annee_id
        assert corps["statut"] == "ACTIF"
        assert len(corps["inscriptions"]) == 1
        assert corps["inscriptions"][0]["tarif_mensuel_cents"] == 20000
        assert corps["frais_inscription"]["montant_cents"] == 5000
        assert corps["frais_inscription"]["statut"] == "NON_PAYE"

    async def test_matricule_incremente_par_annee(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin2@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        donnees = _donnees_eleve(niveau_code, matiere_id)
        r1 = await client.post("/api/eleves", json=donnees, headers=headers)
        r2 = await client.post("/api/eleves", json=donnees, headers=headers)

        assert r1.json()["matricule"] == "E-2025-0001"
        assert r2.json()["matricule"] == "E-2025-0002"

    async def test_modifier_le_tarif_referentiel_ne_change_pas_inscription_existante(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Décision D1, le test le plus important de l'étape 3."""
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        assert creation.json()["inscriptions"][0]["tarif_mensuel_cents"] == 20000
        eleve_id = creation.json()["id"]

        # L'administrateur augmente le tarif du référentiel après coup.
        rep_maj_tarif = await client.put(
            "/api/referentiel/tarifs-eleve",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "matiere_id": matiere_id,
                "montant_cents": 99999,
            },
            headers=headers,
        )
        assert rep_maj_tarif.status_code == 200
        assert rep_maj_tarif.json()["montant_cents"] == 99999

        # L'inscription déjà créée ne doit STRICTEMENT PAS avoir bougé.
        fiche = await client.get(f"/api/eleves/{eleve_id}", headers=headers)
        assert fiche.json()["inscriptions"][0]["tarif_mensuel_cents"] == 20000

    async def test_refuse_sans_annee_active(self, client: AsyncClient, session: AsyncSession):
        annee = await creer_annee_scolaire(session, active=False)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        await creer_tarif_eleve(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin4@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json=_donnees_eleve(niveau.code, matiere.id),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 422

    async def test_refuse_si_aucun_tarif_defini(self, client: AsyncClient, session: AsyncSession):
        await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        # Pas de tarif_eleve créé pour ce couple.
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin5@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json=_donnees_eleve(niveau.code, matiere.id),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 404

    async def test_caissier_peut_creer(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )

        reponse = await client.post(
            "/api/eleves",
            json=_donnees_eleve(niveau_code, matiere_id),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 201

    async def test_professeur_refuse(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )

        reponse = await client.post(
            "/api/eleves",
            json=_donnees_eleve(niveau_code, matiere_id),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.get("/api/eleves")
        assert reponse.status_code == 401


class TestListeEtFiltres:
    async def test_recherche_et_filtre_niveau(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin6@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        autre = _donnees_eleve(niveau_code, matiere_id)
        autre["nom"] = "Benali"
        autre["prenom"] = "Sara"
        await client.post("/api/eleves", json=autre, headers=headers)

        reponse = await client.get("/api/eleves?recherche=Alaoui", headers=headers)
        assert reponse.status_code == 200
        assert reponse.json()["total"] == 1
        assert reponse.json()["elements"][0]["nom"] == "Alaoui"

        reponse_niveau = await client.get(
            f"/api/eleves?niveau_code={niveau_code}", headers=headers
        )
        assert reponse_niveau.json()["total"] == 2

    async def test_pagination(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin7@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        for i in range(3):
            donnees = _donnees_eleve(niveau_code, matiere_id)
            donnees["nom"] = f"Nom{i}"
            await client.post("/api/eleves", json=donnees, headers=headers)

        reponse = await client.get("/api/eleves?page=1&taille=2", headers=headers)
        assert reponse.json()["total"] == 3
        assert len(reponse.json()["elements"]) == 2


class TestChangementStatut:
    async def test_archiver_un_eleve(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin8@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        eleve_id = creation.json()["id"]

        reponse = await client.post(
            f"/api/eleves/{eleve_id}/statut", json={"statut": "ARCHIVE"}, headers=headers
        )
        assert reponse.status_code == 200
        assert reponse.json()["statut"] == "ARCHIVE"

    async def test_caissier_ne_peut_pas_changer_statut_sans_jeton_valide(
        self, client: AsyncClient
    ):
        reponse = await client.post("/api/eleves/1/statut", json={"statut": "ARCHIVE"})
        assert reponse.status_code == 401
