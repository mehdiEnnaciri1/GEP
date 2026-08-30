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
from app.shared.periode import periode_courante, periode_precedente, periode_suivante
from tests.factories.referentiel import (
    creer_annee_scolaire,
    creer_matiere,
    creer_niveau,
    creer_tarif_eleve,
    creer_tarif_pack,
)
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur


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

    async def test_matricule_incremente_par_annee(self, client: AsyncClient, session: AsyncSession):
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


async def _preparer_pack(session: AsyncSession, *, montant_pack: int = 45000):
    """Année + niveau + 2 matières tarifées + tarif pack. Retourne
    (annee_id, niveau_code, matiere_math_id, matiere_svt_id)."""
    annee = await creer_annee_scolaire(session)
    niveau = await creer_niveau(session)
    matiere_math = await creer_matiere(session, code="MATH", libelle="Mathématiques")
    matiere_svt = await creer_matiere(session, code="SVT", libelle="SVT")
    await creer_tarif_eleve(
        session,
        annee_scolaire_id=annee.id,
        niveau_code=niveau.code,
        matiere_id=matiere_math.id,
        montant_cents=30000,
    )
    await creer_tarif_eleve(
        session,
        annee_scolaire_id=annee.id,
        niveau_code=niveau.code,
        matiere_id=matiere_svt.id,
        montant_cents=25000,
    )
    await creer_tarif_pack(
        session, annee_scolaire_id=annee.id, niveau_code=niveau.code, montant_cents=montant_pack
    )
    return annee.id, niveau.code, matiere_math.id, matiere_svt.id


class TestPack:
    """Le pack désigne LITTÉRALEMENT toutes les matières tarifées du niveau —
    voir docs/adr/2026-08-29-pack-et-reduction.md. Chaque matière reste une
    inscription réelle (tarif fractionné), donc comptée normalement par la
    paie professeur : ce n'est qu'un mode de tarification côté élève."""

    async def test_pack_inscrit_toutes_les_matieres_au_tarif_fractionne(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_math_id, matiere_svt_id = await _preparer_pack(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack1@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json={
                "nom": "Bennani",
                "prenom": "Sara",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                # matiere_ids envoyé quand même, doit être ignoré au profit
                # des matières tarifées du niveau.
                "matiere_ids": [],
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )

        assert reponse.status_code == 201
        corps = reponse.json()
        assert corps["est_pack"] is True
        assert corps["reduction_mensuelle_cents"] is None
        matieres_inscrites = {i["matiere_id"] for i in corps["inscriptions"]}
        assert matieres_inscrites == {matiere_math_id, matiere_svt_id}
        # 45000 / 2 = 22500 pile — pas de reste à distribuer ici.
        tarifs = {i["matiere_id"]: i["tarif_mensuel_cents"] for i in corps["inscriptions"]}
        assert tarifs[matiere_math_id] == 22500
        assert tarifs[matiere_svt_id] == 22500
        assert sum(tarifs.values()) == 45000

    async def test_pack_fractionnement_avec_reste_sur_premiere_matiere(
        self, client: AsyncClient, session: AsyncSession
    ):
        # 46000 / 2 = 23000, reste 0 -> pas de cas intéressant. Choisir un
        # montant qui ne se divise pas exactement pour vérifier le reste.
        _, niveau_code, matiere_math_id, matiere_svt_id = await _preparer_pack(
            session, montant_pack=45001
        )
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack1b@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json={
                "nom": "Bennani",
                "prenom": "Sara",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                "matiere_ids": [],
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 201
        tarifs = {i["matiere_id"]: i["tarif_mensuel_cents"] for i in reponse.json()["inscriptions"]}
        # id le plus petit (matiere_math_id, créée en premier) reçoit le reste.
        premiere_matiere_id = min(matiere_math_id, matiere_svt_id)
        assert tarifs[premiere_matiere_id] == 22501
        assert sum(tarifs.values()) == 45001

    async def test_pack_refuse_si_aucun_tarif_pack_defini(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee_id, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack2@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json={
                "nom": "Bennani",
                "prenom": "Sara",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                "matiere_ids": [],
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 404

    async def test_activer_pack_remplace_les_inscriptions_individuelles(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_math_id, matiere_svt_id = await _preparer_pack(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves",
            json={
                "nom": "Idrissi",
                "prenom": "Nadia",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "matiere_ids": [matiere_math_id],
            },
            headers=headers,
        )
        eleve_id = creation.json()["id"]
        ancienne_inscription_id = creation.json()["inscriptions"][0]["id"]

        activation = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={"periode_application": periode_courante(), "est_pack": True},
            headers=headers,
        )
        assert activation.status_code == 200
        corps = activation.json()
        assert corps["est_pack"] is True

        actives = [i for i in corps["inscriptions"] if i["date_fin"] is None]
        closes = [i for i in corps["inscriptions"] if i["date_fin"] is not None]
        assert {i["matiere_id"] for i in actives} == {matiere_math_id, matiere_svt_id}
        assert any(i["id"] == ancienne_inscription_id for i in closes)

    async def test_desactiver_pack_bascule_vers_les_matieres_choisies(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Désactiver le pack, c'est remplacer l'engagement par un choix de
        matières réel — pas le vider : l'élève ne peut pas se retrouver sans
        aucune matière suivie (voir ModifierEngagement)."""
        _, niveau_code, matiere_math_id, _ = await _preparer_pack(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack4@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves",
            json={
                "nom": "Idrissi",
                "prenom": "Nadia",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                "matiere_ids": [],
            },
            headers=headers,
        )
        eleve_id = creation.json()["id"]

        desactivation = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={
                "periode_application": periode_courante(),
                "est_pack": False,
                "matiere_ids": [matiere_math_id],
            },
            headers=headers,
        )
        assert desactivation.status_code == 200
        corps = desactivation.json()
        assert corps["est_pack"] is False
        anciennes = [i for i in corps["inscriptions"] if i["date_fin"] is not None]
        nouvelles = [i for i in corps["inscriptions"] if i["date_fin"] is None]
        assert len(anciennes) == 2  # les 2 matières du pack, closes
        assert {i["matiere_id"] for i in nouvelles} == {matiere_math_id}

    async def test_modifier_tarif_pack_referentiel_ne_change_pas_eleve_deja_inscrit(
        self, client: AsyncClient, session: AsyncSession
    ):
        """D1 étendu au pack : le forfait est copié à l'engagement."""
        annee_id, niveau_code, matiere_math_id, matiere_svt_id = await _preparer_pack(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack5@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves",
            json={
                "nom": "Bennani",
                "prenom": "Sara",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                "matiere_ids": [],
            },
            headers=headers,
        )
        eleve_id = creation.json()["id"]

        maj = await client.put(
            "/api/referentiel/tarifs-pack",
            json={
                "annee_scolaire_id": annee_id,
                "niveau_code": niveau_code,
                "montant_cents": 99999,
            },
            headers=headers,
        )
        assert maj.status_code == 200

        fiche = await client.get(f"/api/eleves/{eleve_id}", headers=headers)
        tarifs = {i["matiere_id"]: i["tarif_mensuel_cents"] for i in fiche.json()["inscriptions"]}
        assert sum(tarifs.values()) == 45000  # toujours l'ancien forfait, pas 99999

    async def test_pack_et_reduction_incompatibles(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, _, _ = await _preparer_pack(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="pack6@test.ma")

        reponse = await client.post(
            "/api/eleves",
            json={
                "nom": "Bennani",
                "prenom": "Sara",
                "telephone_parent": "0600000000",
                "niveau_code": niveau_code,
                "date_inscription": "2025-09-15",
                "est_pack": True,
                "reduction_mensuelle_cents": 10000,
                "matiere_ids": [],
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert reponse.status_code == 422


class TestReduction:
    async def test_reduction_utilise_le_montant_saisi_matieres_reelles_inchangees(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="reduc1@test.ma")

        donnees = _donnees_eleve(niveau_code, matiere_id)
        donnees["reduction_mensuelle_cents"] = 15000

        reponse = await client.post(
            "/api/eleves", json=donnees, headers={"Authorization": f"Bearer {jeton}"}
        )
        assert reponse.status_code == 201
        corps = reponse.json()
        assert corps["reduction_mensuelle_cents"] == 15000
        assert corps["est_pack"] is False
        # L'inscription garde le vrai tarif de la matière (paie professeur
        # inchangée), la réduction ne s'applique qu'à l'échéance.
        assert corps["inscriptions"][0]["tarif_mensuel_cents"] == 20000

    async def test_reduction_negative_refusee(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="reduc2@test.ma")

        donnees = _donnees_eleve(niveau_code, matiere_id)
        donnees["reduction_mensuelle_cents"] = -100

        reponse = await client.post(
            "/api/eleves", json=donnees, headers={"Authorization": f"Bearer {jeton}"}
        )
        assert reponse.status_code == 422

    async def test_activer_puis_desactiver_reduction_remet_a_null(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="reduc3@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        eleve_id = creation.json()["id"]
        assert creation.json()["reduction_mensuelle_cents"] is None

        activation = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={
                "periode_application": periode_courante(),
                "reduction_mensuelle_cents": 12000,
                "matiere_ids": [matiere_id],
            },
            headers=headers,
        )
        assert activation.status_code == 200
        assert activation.json()["reduction_mensuelle_cents"] == 12000

        desactivation = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={"periode_application": periode_courante(), "matiere_ids": [matiere_id]},
            headers=headers,
        )
        assert desactivation.status_code == 200
        assert desactivation.json()["reduction_mensuelle_cents"] is None

    async def test_engagement_pack_et_reduction_incompatibles(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(client, session, role=RoleUtilisateur.ADMIN, email="reduc4@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        eleve_id = creation.json()["id"]

        reponse = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={
                "periode_application": periode_courante(),
                "est_pack": True,
                "reduction_mensuelle_cents": 10000,
            },
            headers=headers,
        )
        assert reponse.status_code == 422


class TestModifierEngagement:
    """Modifier les matières, le pack ou la réduction d'un élève déjà
    inscrit, à partir d'un mois choisi — avant cette fonctionnalité, un
    élève NORMAL (ni pack ni réduction) ne pouvait jamais changer de
    matières après sa création."""

    async def test_ajoute_une_matiere_a_partir_du_mois_choisi(
        self, client: AsyncClient, session: AsyncSession
    ):
        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere_maths = await creer_matiere(session, code="MATH", libelle="Maths")
        matiere_svt = await creer_matiere(session, code="SVT", libelle="SVT")
        await creer_tarif_eleve(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_maths.id,
            montant_cents=20000,
        )
        await creer_tarif_eleve(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_svt.id,
            montant_cents=15000,
        )
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="engagement1@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves",
            json={
                "nom": "Fassi",
                "prenom": "Omar",
                "telephone_parent": "0600000000",
                "niveau_code": niveau.code,
                "date_inscription": "2025-09-15",
                "matiere_ids": [matiere_maths.id],
            },
            headers=headers,
        )
        eleve_id = creation.json()["id"]
        ancienne_inscription_id = creation.json()["inscriptions"][0]["id"]

        mois_prochain = periode_suivante(periode_courante())
        modification = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={
                "periode_application": mois_prochain,
                "matiere_ids": [matiere_maths.id, matiere_svt.id],
            },
            headers=headers,
        )
        assert modification.status_code == 200
        corps = modification.json()
        actives = [i for i in corps["inscriptions"] if i["date_fin"] is None]
        closes = [i for i in corps["inscriptions"] if i["date_fin"] is not None]
        assert {i["matiere_id"] for i in actives} == {matiere_maths.id, matiere_svt.id}
        assert any(i["id"] == ancienne_inscription_id for i in closes)
        assert all(i["date_debut"] == f"{mois_prochain}-01" for i in actives)

    async def test_refuse_un_mois_deja_passe(self, client: AsyncClient, session: AsyncSession):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="engagement2@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        eleve_id = creation.json()["id"]

        reponse = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={
                "periode_application": periode_precedente(periode_courante()),
                "matiere_ids": [matiere_id],
            },
            headers=headers,
        )
        assert reponse.status_code == 422

    async def test_refuse_un_mois_dont_lecheance_est_deja_generee(
        self, client: AsyncClient, session: AsyncSession
    ):
        _, niveau_code, matiere_id = await _preparer_referentiel(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.ADMIN, email="engagement3@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}

        creation = await client.post(
            "/api/eleves", json=_donnees_eleve(niveau_code, matiere_id), headers=headers
        )
        eleve_id = creation.json()["id"]

        periode = periode_courante()
        genere = await client.post(
            "/api/paiements/generer-echeances", json={"periode": periode}, headers=headers
        )
        assert genere.status_code == 200

        reponse = await client.post(
            f"/api/eleves/{eleve_id}/engagement",
            json={"periode_application": periode, "matiere_ids": [matiere_id]},
            headers=headers,
        )
        assert reponse.status_code == 409


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

        reponse_niveau = await client.get(f"/api/eleves?niveau_code={niveau_code}", headers=headers)
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

    async def test_caissier_ne_peut_pas_changer_statut_sans_jeton_valide(self, client: AsyncClient):
        reponse = await client.post("/api/eleves/1/statut", json={"statut": "ARCHIVE"})
        assert reponse.status_code == 401
