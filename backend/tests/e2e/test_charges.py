"""Tests e2e du module charges — catégories, création avec justificatif
(type MIME vérifié sur les octets réels), totaux par période/catégorie,
annulation, permissions (§6.6 : ADMIN complet, CAISSIER et PROFESSEUR sans
aucun accès, pas même en lecture)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur

PERIODE = "2025-10"
JPEG_MINIMAL = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PDF_MINIMAL = b"%PDF-1.4\n" + b"\x00" * 20


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


def _donnees_charge(categorie_id: int, **overrides: object) -> dict:
    base = {
        "categorie_id": str(categorie_id),
        "description": "Facture Lydec octobre",
        "montant_cents": "50000",
        "date_charge": "2025-11-05",
        "periode": PERIODE,
        "mode_paiement": "VIREMENT",
    }
    base.update({k: str(v) for k, v in overrides.items()})
    return base


class TestCategories:
    async def test_admin_cree_une_categorie(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin1@test.ma")
        rep = await client.post(
            "/api/charges/categories",
            json={"libelle": "Loyer"},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 201

    async def test_libelle_duplique_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin2@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        await client.post("/api/charges/categories", json={"libelle": "Eau"}, headers=headers)
        rep = await client.post("/api/charges/categories", json={"libelle": "Eau"}, headers=headers)
        assert rep.status_code == 409

    async def test_caissier_ne_peut_pas_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        rep = await client.get(
            "/api/charges/categories", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 403

    async def test_professeur_ne_peut_pas_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )
        rep = await client.get(
            "/api/charges/categories", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get("/api/charges/categories")
        assert rep.status_code == 401


class TestCreationCharge:
    async def test_admin_cree_une_charge_sans_justificatif(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post(
                "/api/charges/categories", json={"libelle": "Internet"}, headers=headers
            )
        ).json()["id"]

        rep = await client.post("/api/charges", data=_donnees_charge(categorie_id), headers=headers)
        assert rep.status_code == 201
        assert rep.json()["montant_cents"] == 50000
        assert rep.json()["periode"] == PERIODE
        assert rep.json()["justificatif_type"] is None

    async def test_admin_cree_une_charge_avec_justificatif_pdf(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin4@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post(
                "/api/charges/categories", json={"libelle": "Fournitures"}, headers=headers
            )
        ).json()["id"]

        rep = await client.post(
            "/api/charges",
            data=_donnees_charge(categorie_id),
            files={"justificatif": ("facture.pdf", PDF_MINIMAL, "application/pdf")},
            headers=headers,
        )
        assert rep.status_code == 201
        assert rep.json()["justificatif_type"] == "application/pdf"

        charge_id = rep.json()["id"]
        justificatif = await client.get(f"/api/charges/{charge_id}/justificatif", headers=headers)
        assert justificatif.status_code == 200
        assert justificatif.content == PDF_MINIMAL
        assert justificatif.headers["content-type"] == "application/pdf"

    async def test_fichier_non_reconnu_refuse(self, client: AsyncClient, session: AsyncSession):
        """Le nom de fichier prétend être un JPEG, le contenu ne l'est pas —
        la détection porte sur les octets réels, pas sur l'extension."""
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin5@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post(
                "/api/charges/categories", json={"libelle": "Entretien"}, headers=headers
            )
        ).json()["id"]

        rep = await client.post(
            "/api/charges",
            data=_donnees_charge(categorie_id),
            files={"justificatif": ("photo.jpg", b"<html>pas une image</html>", "image/jpeg")},
            headers=headers,
        )
        assert rep.status_code == 422

    async def test_categorie_introuvable(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin6@test.ma")
        rep = await client.post(
            "/api/charges",
            data=_donnees_charge(999999),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 404

    async def test_caissier_ne_peut_pas_creer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.post(
            "/api/charges",
            data=_donnees_charge(1),
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.post("/api/charges", data=_donnees_charge(1))
        assert rep.status_code == 401


class TestListeEtTotaux:
    async def test_liste_filtree_par_periode(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin7@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post("/api/charges/categories", json={"libelle": "Loyer"}, headers=headers)
        ).json()["id"]

        await client.post("/api/charges", data=_donnees_charge(categorie_id), headers=headers)
        await client.post(
            "/api/charges",
            data=_donnees_charge(categorie_id, periode="2025-11"),
            headers=headers,
        )

        rep = await client.get(f"/api/charges?periode={PERIODE}", headers=headers)
        assert rep.status_code == 200
        assert len(rep.json()) == 1
        assert rep.json()[0]["periode"] == PERIODE

    async def test_totaux_par_periode_et_categorie(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin8@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_loyer = (
            await client.post("/api/charges/categories", json={"libelle": "Loyer"}, headers=headers)
        ).json()["id"]
        categorie_eau = (
            await client.post("/api/charges/categories", json={"libelle": "Eau"}, headers=headers)
        ).json()["id"]

        await client.post(
            "/api/charges",
            data=_donnees_charge(categorie_loyer, montant_cents=300000),
            headers=headers,
        )
        await client.post(
            "/api/charges",
            data=_donnees_charge(categorie_eau, montant_cents=15000),
            headers=headers,
        )

        rep = await client.get(f"/api/charges/totaux?periode={PERIODE}", headers=headers)
        assert rep.status_code == 200
        assert rep.json()["total_cents"] == 315000
        par_categorie = {p["categorie_id"]: p["total_cents"] for p in rep.json()["par_categorie"]}
        assert par_categorie[categorie_loyer] == 300000
        assert par_categorie[categorie_eau] == 15000

    async def test_caissier_ne_peut_pas_consulter_totaux(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.get(
            f"/api/charges/totaux?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403


class TestAnnulation:
    async def test_admin_annule_une_charge(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin9@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post(
                "/api/charges/categories", json={"libelle": "Publicité"}, headers=headers
            )
        ).json()["id"]
        charge_id = (
            await client.post("/api/charges", data=_donnees_charge(categorie_id), headers=headers)
        ).json()["id"]

        rep = await client.post(f"/api/charges/{charge_id}/annuler", headers=headers)
        assert rep.status_code == 200
        assert rep.json()["annule_le"] is not None

        # Une charge annulée n'apparaît plus dans la liste ni les totaux.
        liste = await client.get(f"/api/charges?periode={PERIODE}", headers=headers)
        assert liste.json() == []
        totaux = await client.get(f"/api/charges/totaux?periode={PERIODE}", headers=headers)
        assert totaux.json()["total_cents"] == 0

    async def test_double_annulation_refusee(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="admin10@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}
        categorie_id = (
            await client.post(
                "/api/charges/categories", json={"libelle": "Autres"}, headers=headers
            )
        ).json()["id"]
        charge_id = (
            await client.post("/api/charges", data=_donnees_charge(categorie_id), headers=headers)
        ).json()["id"]

        await client.post(f"/api/charges/{charge_id}/annuler", headers=headers)
        rep = await client.post(f"/api/charges/{charge_id}/annuler", headers=headers)
        assert rep.status_code == 409

    async def test_caissier_ne_peut_pas_annuler(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier4@test.ma"
        )
        rep = await client.post(
            "/api/charges/1/annuler", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 403
