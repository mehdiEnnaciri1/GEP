"""Tests e2e du module paiements — génération des échéances, encaissement
(frais d'inscription et mensualité), idempotence, permissions, et surtout
l'ANNULATION : le recalcul du statut d'échéance après annulation est
l'endroit où les bugs se logent (voir CLAUDE.md), ces tests l'exercent en
détail : paiement complet annulé, un des deux paiements partiels annulé,
frais d'inscription annulé, double annulation refusée.
"""

from __future__ import annotations

import uuid

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

PERIODE = "2025-10"


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


async def _creer_eleve_avec_inscription(
    client: AsyncClient, session: AsyncSession, headers: dict, *, tarif_cents: int = 20000
) -> tuple[int, str, int]:
    """Retourne (eleve_id, niveau_code, matiere_id)."""
    annee = await creer_annee_scolaire(session)
    niveau = await creer_niveau(session)
    matiere = await creer_matiere(session)
    await creer_tarif_eleve(
        session,
        annee_scolaire_id=annee.id,
        niveau_code=niveau.code,
        matiere_id=matiere.id,
        montant_cents=tarif_cents,
    )

    reponse = await client.post(
        "/api/eleves",
        json={
            "nom": "Alaoui",
            "prenom": "Yassine",
            "telephone_parent": "0600000000",
            "niveau_code": niveau.code,
            "date_inscription": "2025-09-15",
            "matiere_ids": [matiere.id],
        },
        headers=headers,
    )
    assert reponse.status_code == 201
    return reponse.json()["id"], niveau.code, matiere.id


class TestGenerationEcheances:
    async def test_genere_une_echeance_par_eleve_actif(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin1@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await _creer_eleve_avec_inscription(client, session, headers, tarif_cents=20000)

        reponse = await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        assert reponse.status_code == 200
        assert reponse.json()["nombre_generees"] == 1

        impayes = await client.get(
            f"/api/paiements/impayes?periode={PERIODE}", headers=headers
        )
        assert len(impayes.json()) == 1
        assert impayes.json()[0]["montant_du_cents"] == 20000
        assert impayes.json()[0]["statut"] == "NON_PAYE"

    async def test_idempotent_ne_duplique_pas(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin2@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await _creer_eleve_avec_inscription(client, session, headers)

        premiere = await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        seconde = await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        assert premiere.json()["nombre_generees"] == 1
        assert seconde.json()["nombre_generees"] == 0

    async def test_caissier_ne_peut_pas_generer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        reponse = await client.post(
            "/api/paiements/generer-echeances",
            json={"periode": PERIODE},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 403


class TestEncaissementFraisInscription:
    async def test_encaissement_reussi(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)

        reponse = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers,
        )
        assert reponse.status_code == 201
        assert reponse.json()["numero_recu"].startswith("R-2025-")

        fiche = await client.get(f"/api/eleves/{eleve_id}", headers=headers)
        assert fiche.json()["frais_inscription"]["statut"] == "PAYE"

    async def test_montant_incorrect_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin4@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)

        reponse = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 1234,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers,
        )
        assert reponse.status_code == 422

    async def test_deja_paye_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin5@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)
        corps = {
            "eleve_id": eleve_id,
            "montant_cents": 5000,
            "mode": "ESPECES",
            "date_paiement": "2025-09-15",
        }
        await client.post("/api/paiements/frais-inscription", json=corps, headers=headers)

        reponse = await client.post(
            "/api/paiements/frais-inscription", json=corps, headers=headers
        )
        assert reponse.status_code == 409

    async def test_idempotence_meme_cle_meme_paiement(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin6@test.ma")
        headers = {
            "Authorization": f"Bearer {jeton}",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)
        corps = {
            "eleve_id": eleve_id,
            "montant_cents": 5000,
            "mode": "ESPECES",
            "date_paiement": "2025-09-15",
        }

        premiere = await client.post(
            "/api/paiements/frais-inscription", json=corps, headers=headers
        )
        seconde = await client.post(
            "/api/paiements/frais-inscription", json=corps, headers=headers
        )
        assert premiere.status_code == 201
        assert seconde.status_code == 201
        assert premiere.json()["id"] == seconde.json()["id"]

    async def test_caissier_peut_encaisser(self, client: AsyncClient, session: AsyncSession):
        jeton_admin = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin7@test.ma"
        )
        eleve_id, _, _ = await _creer_eleve_avec_inscription(
            client, session, {"Authorization": f"Bearer {jeton_admin}"}
        )
        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )

        reponse = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert reponse.status_code == 201


class TestEncaissementMensualite:
    async def test_paiement_partiel_puis_complement(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin8@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await _creer_eleve_avec_inscription(client, session, headers, tarif_cents=30000)
        await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        eleve_id = (await client.get("/api/eleves?taille=1", headers=headers)).json()[
            "elements"
        ][0]["id"]

        partiel = await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 10000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-05",
            },
            headers=headers,
        )
        assert partiel.status_code == 201

        impayes = await client.get(
            f"/api/paiements/impayes?periode={PERIODE}", headers=headers
        )
        assert impayes.json()[0]["statut"] == "PARTIEL"
        assert impayes.json()[0]["montant_paye_cents"] == 10000

        await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 20000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-20",
            },
            headers=headers,
        )
        impayes_apres = await client.get(
            f"/api/paiements/impayes?periode={PERIODE}", headers=headers
        )
        assert len(impayes_apres.json()) == 0  # PAYE n'apparaît plus dans les impayés

    async def test_echeance_inexistante_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin9@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)
        # Pas de génération d'échéance pour PERIODE.

        reponse = await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 10000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-05",
            },
            headers=headers,
        )
        assert reponse.status_code == 404


class TestAnnulation:
    """Le cœur de l'étape 4 : le recalcul du statut d'échéance après
    annulation, pas une transition ad hoc."""

    async def test_annuler_un_paiement_complet_revient_a_non_paye(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin10@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        await _creer_eleve_avec_inscription(client, session, headers, tarif_cents=30000)
        await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        eleve_id = (await client.get("/api/eleves?taille=1", headers=headers)).json()[
            "elements"
        ][0]["id"]

        paiement = await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 30000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-05",
            },
            headers=headers,
        )
        paiement_id = paiement.json()["id"]

        avant = await client.get(f"/api/paiements/impayes?periode={PERIODE}", headers=headers)
        assert len(avant.json()) == 0  # PAYE, donc absent des impayés

        annulation = await client.post(
            f"/api/paiements/{paiement_id}/annuler",
            json={"motif": "erreur de saisie"},
            headers=headers,
        )
        assert annulation.status_code == 200
        assert annulation.json()["annule_le"] is not None

        apres = await client.get(f"/api/paiements/impayes?periode={PERIODE}", headers=headers)
        assert len(apres.json()) == 1
        assert apres.json()[0]["statut"] == "NON_PAYE"
        assert apres.json()[0]["montant_paye_cents"] == 0

    async def test_annuler_un_des_deux_paiements_partiels(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Échéance de 300 DH, deux paiements de 100 et 150 DH (statut
        PARTIEL). Annuler celui de 150 DH doit laisser 100 DH payés, statut
        toujours PARTIEL — pas revenir à NON_PAYE, pas rester à 250."""
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin11@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        await _creer_eleve_avec_inscription(client, session, headers, tarif_cents=30000)
        await client.post(
            "/api/paiements/generer-echeances", json={"periode": PERIODE}, headers=headers
        )
        eleve_id = (await client.get("/api/eleves?taille=1", headers=headers)).json()[
            "elements"
        ][0]["id"]

        await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 10000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-05",
            },
            headers=headers,
        )
        deuxieme = await client.post(
            "/api/paiements/mensualite",
            json={
                "eleve_id": eleve_id,
                "periode": PERIODE,
                "montant_cents": 15000,
                "mode": "ESPECES",
                "date_paiement": "2025-10-10",
            },
            headers=headers,
        )

        impayes_avant = await client.get(
            f"/api/paiements/impayes?periode={PERIODE}", headers=headers
        )
        assert impayes_avant.json()[0]["montant_paye_cents"] == 25000
        assert impayes_avant.json()[0]["statut"] == "PARTIEL"

        await client.post(
            f"/api/paiements/{deuxieme.json()['id']}/annuler",
            json={"motif": "chèque impayé"},
            headers=headers,
        )

        impayes_apres = await client.get(
            f"/api/paiements/impayes?periode={PERIODE}", headers=headers
        )
        assert impayes_apres.json()[0]["montant_paye_cents"] == 10000
        assert impayes_apres.json()[0]["statut"] == "PARTIEL"

    async def test_annuler_paiement_frais_inscription(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin12@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)

        paiement = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers,
        )
        fiche_avant = await client.get(f"/api/eleves/{eleve_id}", headers=headers)
        assert fiche_avant.json()["frais_inscription"]["statut"] == "PAYE"

        await client.post(
            f"/api/paiements/{paiement.json()['id']}/annuler",
            json={"motif": "remboursement"},
            headers=headers,
        )

        fiche_apres = await client.get(f"/api/eleves/{eleve_id}", headers=headers)
        assert fiche_apres.json()["frais_inscription"]["statut"] == "NON_PAYE"

        # Et l'élève peut de nouveau régler ses frais (paiement_id bien délié).
        nouveau = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-20",
            },
            headers=headers,
        )
        assert nouveau.status_code == 201

    async def test_double_annulation_refusee(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin13@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)
        paiement = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers,
        )
        paiement_id = paiement.json()["id"]

        premiere = await client.post(
            f"/api/paiements/{paiement_id}/annuler",
            json={"motif": "erreur"},
            headers=headers,
        )
        seconde = await client.post(
            f"/api/paiements/{paiement_id}/annuler",
            json={"motif": "encore"},
            headers=headers,
        )
        assert premiere.status_code == 200
        assert seconde.status_code == 409

    async def test_caissier_ne_peut_pas_annuler(self, client: AsyncClient, session: AsyncSession):
        jeton_admin = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin14@test.ma"
        )
        headers_admin = {"Authorization": f"Bearer {jeton_admin}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers_admin)
        paiement = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers_admin,
        )

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        reponse = await client.post(
            f"/api/paiements/{paiement.json()['id']}/annuler",
            json={"motif": "tentative"},
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert reponse.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        reponse = await client.post("/api/paiements/1/annuler", json={"motif": "x"})
        assert reponse.status_code == 401


class TestHistorique:
    async def test_historique_inclut_les_paiements_annules(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="admin15@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        eleve_id, _, _ = await _creer_eleve_avec_inscription(client, session, headers)
        paiement = await client.post(
            "/api/paiements/frais-inscription",
            json={
                "eleve_id": eleve_id,
                "montant_cents": 5000,
                "mode": "ESPECES",
                "date_paiement": "2025-09-15",
            },
            headers=headers,
        )
        await client.post(
            f"/api/paiements/{paiement.json()['id']}/annuler",
            json={"motif": "erreur"},
            headers=headers,
        )

        historique = await client.get(
            f"/api/paiements/historique/{eleve_id}", headers=headers
        )
        assert len(historique.json()) == 1
        assert historique.json()[0]["annule_le"] is not None
