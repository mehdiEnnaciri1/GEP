"""Tests e2e du module dashboard — un jeu de données connu, chaque
indicateur vérifié contre une valeur calculée à la main (§9 du cahier des
charges, §8.4 de docs/02-modele-donnees.md, décision D2 pour le bénéfice
net). Permissions : CAISSIER n'a droit qu'à la vue restreinte (ni charges,
ni paie, ni bénéfice net), PROFESSEUR n'a droit à rien."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from app.modules.charges.models import CategorieCharge, Charge
from app.modules.eleves.models import Eleve, InscriptionMatiere, StatutEleve
from app.modules.paie.models import PaieMensuelle, StatutPaie
from app.modules.paiements.models import (
    Echeance,
    ModePaiement,
    Paiement,
    StatutEcheance,
    TypePaiement,
)
from tests.factories.professeurs import creer_professeur
from tests.factories.referentiel import creer_annee_scolaire, creer_matiere, creer_niveau
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur

PERIODE = "2025-10"


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


async def _jeton_admin(client: AsyncClient, session: AsyncSession) -> tuple[str, int]:
    utilisateur = await construire_utilisateur(
        session, email="admin@test.ma", role=RoleUtilisateur.ADMIN
    )
    session.add(utilisateur)
    await session.commit()
    await session.refresh(utilisateur)

    reponse = await client.post(
        "/api/auth/login", json={"email": "admin@test.ma", "mot_de_passe": MOT_DE_PASSE_TEST}
    )
    assert reponse.status_code == 200
    return str(reponse.json()["access_token"]), utilisateur.id


async def _construire_jeu_de_donnees(session: AsyncSession, utilisateur_id: int) -> None:
    """Dataset connu — valeurs attendues (calculées à la main) :

    - nombre_eleves_total = 3 (2 en 1BAC, 1 en 2BAC)
    - nombre_eleves_par_niveau = {1BAC: 2, 2BAC: 1}
    - nombre_professeurs = 3 (dont un rattaché à la seule paie BROUILLON)
    - encaissements_mensualites = 20000 + 15000 = 35000
    - encaissements_inscriptions = 5000
    - montant_total_encaisse = 40000
    - montant_frais_inscription_cumules (vue CAISSIER, brut) = 5000
    - montant_frais_inscription_cumules (vue ADMIN, net du loyer) =
      frais_inscription(5000) - (charges(15000) - loyer(10000)) = 0
    - montant_impayes = (25000-10000) + (20000-5000) = 15000 + 15000 = 30000
    - total_charges = 10000 + 5000 = 15000
    - total_paie (hors BROUILLON) = 12000 (la paie BROUILLON à 99999 est ignorée)
    - benefice_net = 40000 - 15000 - 12000 = 13000
    """
    annee = await creer_annee_scolaire(session)
    niveau_1bac = await creer_niveau(session, code="1BAC", ordre=5)
    niveau_2bac = await creer_niveau(session, code="2BAC", ordre=6)

    premier_eleve = Eleve(
        matricule="1BAC-0",
        nom="Eleve",
        prenom="1BAC-0",
        telephone_parent="0600000000",
        niveau_code=niveau_1bac.code,
        annee_scolaire_id=annee.id,
        date_inscription=date(2025, 9, 1),
        statut=StatutEleve.ACTIF,
        cree_par=utilisateur_id,
    )
    deuxieme_eleve = Eleve(
        matricule="1BAC-1",
        nom="Eleve",
        prenom="1BAC-1",
        telephone_parent="0600000000",
        niveau_code=niveau_1bac.code,
        annee_scolaire_id=annee.id,
        date_inscription=date(2025, 9, 1),
        statut=StatutEleve.ACTIF,
        cree_par=utilisateur_id,
    )
    session.add(premier_eleve)
    session.add(deuxieme_eleve)
    session.add(
        Eleve(
            matricule="2BAC-0",
            nom="Eleve",
            prenom="2BAC-0",
            telephone_parent="0600000000",
            niveau_code=niveau_2bac.code,
            annee_scolaire_id=annee.id,
            date_inscription=date(2025, 9, 1),
            statut=StatutEleve.ACTIF,
            cree_par=utilisateur_id,
        )
    )
    await session.flush()
    # Deux élèves distincts pour les deux échéances ci-dessous : ux_echeance
    # est UNIQUE (eleve_id, periode), les deux lignes ne peuvent pas partager
    # le même élève pour la même période.
    eleve_id = premier_eleve.id
    autre_eleve_id = deuxieme_eleve.id

    await creer_professeur(session, nom="Alaoui", prenom="Karim")
    professeur_2 = await creer_professeur(session, nom="Bennani", prenom="Yassine")

    session.add_all(
        [
            Paiement(
                numero_recu="R-2025-000001",
                eleve_id=eleve_id,
                type=TypePaiement.MENSUALITE,
                periode=PERIODE,
                montant_cents=20000,
                date_paiement=date(2025, 10, 5),
                mode=ModePaiement.VIREMENT,
                cree_par=utilisateur_id,
            ),
            Paiement(
                numero_recu="R-2025-000002",
                eleve_id=eleve_id,
                type=TypePaiement.MENSUALITE,
                periode=PERIODE,
                montant_cents=15000,
                date_paiement=date(2025, 10, 10),
                mode=ModePaiement.ESPECES,
                cree_par=utilisateur_id,
            ),
            Paiement(
                numero_recu="R-2025-000003",
                eleve_id=eleve_id,
                type=TypePaiement.INSCRIPTION,
                periode=None,
                montant_cents=5000,
                date_paiement=date(2025, 10, 15),
                mode=ModePaiement.ESPECES,
                cree_par=utilisateur_id,
            ),
            Echeance(
                eleve_id=eleve_id,
                periode=PERIODE,
                montant_du_cents=25000,
                montant_paye_cents=10000,
                statut=StatutEcheance.PARTIEL,
            ),
            Echeance(
                eleve_id=autre_eleve_id,
                periode=PERIODE,
                montant_du_cents=20000,
                montant_paye_cents=5000,
                statut=StatutEcheance.PARTIEL,
            ),
        ]
    )

    categorie_loyer = CategorieCharge(libelle="Loyer")
    categorie_eau = CategorieCharge(libelle="Eau")
    session.add_all([categorie_loyer, categorie_eau])
    await session.flush()
    session.add_all(
        [
            Charge(
                categorie_id=categorie_loyer.id,
                description="Loyer octobre",
                montant_cents=10000,
                date_charge=date(2025, 10, 1),
                periode=PERIODE,
                mode_paiement=ModePaiement.VIREMENT,
                cree_par=utilisateur_id,
            ),
            Charge(
                categorie_id=categorie_eau.id,
                description="Facture eau",
                montant_cents=5000,
                date_charge=date(2025, 10, 20),
                periode=PERIODE,
                mode_paiement=ModePaiement.ESPECES,
                cree_par=utilisateur_id,
            ),
        ]
    )

    await session.flush()
    session.add_all(
        [
            PaieMensuelle(
                professeur_id=professeur_2.id,
                periode=PERIODE,
                total_cents=12000,
                statut=StatutPaie.VALIDEE,
            ),
        ]
    )
    await session.flush()
    # Une deuxième paie, en BROUILLON, ne doit PAS compter dans total_paie.
    autre_professeur = await creer_professeur(session, nom="Idrissi", prenom="Sara")
    session.add(
        PaieMensuelle(
            professeur_id=autre_professeur.id,
            periode=PERIODE,
            total_cents=99999,
            statut=StatutPaie.BROUILLON,
        )
    )
    await session.commit()


class TestIndicateurs:
    async def test_indicateurs_complets_verifies_un_par_un(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)

        rep = await client.get(
            f"/api/dashboard/complet?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 200
        d = rep.json()

        assert d["nombre_eleves_total"] == 3
        par_niveau = {n["niveau_code"]: n["nombre"] for n in d["nombre_eleves_par_niveau"]}
        assert par_niveau == {"1BAC": 2, "2BAC": 1}
        assert d["nombre_professeurs"] == 3  # 2 créés explicitement + 1 pour la paie BROUILLON
        assert d["montant_total_encaisse_cents"] == 40000
        # Vue ADMIN : net du loyer, PAS le brut (5000) que voit le CAISSIER
        # (voir test_caissier_vue_restreinte_sans_charges_ni_paie_ni_benefice).
        assert d["montant_frais_inscription_cumules_cents"] == 0
        assert d["montant_impayes_cents"] == 30000
        assert d["total_charges_cents"] == 15000
        assert d["total_paie_cents"] == 12000
        assert d["benefice_net_cents"] == 13000

    async def test_caissier_vue_restreinte_sans_charges_ni_paie_ni_benefice(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton_admin, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        rep = await client.get(
            f"/api/dashboard/restreint?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert rep.status_code == 200
        d = rep.json()
        assert d["montant_total_encaisse_cents"] == 40000
        # Vue CAISSIER : le brut (5000), jamais le calcul net du loyer, qui
        # exposerait indirectement les charges à un rôle qui n'y a pas accès.
        assert d["montant_frais_inscription_cumules_cents"] == 5000
        assert "total_charges_cents" not in d
        assert "total_paie_cents" not in d
        assert "benefice_net_cents" not in d

    async def test_caissier_ne_peut_pas_acceder_a_la_vue_complete(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.get(
            f"/api/dashboard/complet?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_professeur_ne_peut_rien_consulter(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}
        assert (
            await client.get(f"/api/dashboard/complet?periode={PERIODE}", headers=headers)
        ).status_code == 403
        assert (
            await client.get(f"/api/dashboard/restreint?periode={PERIODE}", headers=headers)
        ).status_code == 403
        assert (await client.get("/api/dashboard/annees-dispo", headers=headers)).status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get(f"/api/dashboard/complet?periode={PERIODE}")
        assert rep.status_code == 401


class TestAnneesDisponibles:
    async def test_admin_liste_les_annees(self, client: AsyncClient, session: AsyncSession):
        jeton, _ = await _jeton_admin(client, session)
        await creer_annee_scolaire(session)
        rep = await client.get(
            "/api/dashboard/annees-dispo", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 200
        assert len(rep.json()) == 1

    async def test_caissier_peut_lister(self, client: AsyncClient, session: AsyncSession):
        await creer_annee_scolaire(session)
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.get(
            "/api/dashboard/annees-dispo", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 200


class TestEvolutionEffectifs:
    """Jeu de données connu, un mois de coupure et un statut par cas — voir
    §8 de docs/02-modele-donnees.md pour la règle de comptage.

    Année scolaire 2025-2026 (août 2025 → juillet 2026) :
    - F, ACTIF, inscrit du 2025-08-01 au 2025-08-31 seulement -> compte en
      août uniquement, plus du tout dès septembre
    - A, ACTIF, inscrit du 2025-09-01 sans fin -> compte de septembre à
      juillet (pas en août, l'inscription n'existait pas encore)
    - B, ACTIF, inscrit du 2025-09-01 au 2025-11-30 -> compte sept/oct/nov,
      plus du tout à partir de décembre
    - C, SUSPENDU, inscrit du 2025-09-01 sans fin -> compte quand même comme
      A (SUSPENDU n'exclut pas, seul ARCHIVE exclut)
    - D, ARCHIVE, inscrit du 2025-09-01 sans fin -> ne compte JAMAIS
    - E, ACTIF, inscrit à partir du 2026-01-15 -> ne compte qu'à partir de
      janvier 2026

    nb attendu par mois : août=1, sept=3, oct=3, nov=3, dec=2, puis jan..juil=3.
    """

    async def test_comptage_mensuel_sur_un_jeu_connu(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        annee = await creer_annee_scolaire(
            session, libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30)
        )
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)

        def _eleve(matricule: str, statut: StatutEleve) -> Eleve:
            return Eleve(
                matricule=matricule,
                nom="Eleve",
                prenom=matricule,
                telephone_parent="0600000000",
                niveau_code=niveau.code,
                annee_scolaire_id=annee.id,
                date_inscription=date(2025, 9, 1),
                statut=statut,
                cree_par=utilisateur_id,
            )

        eleve_f = _eleve("EFF-F", StatutEleve.ACTIF)
        eleve_a = _eleve("EFF-A", StatutEleve.ACTIF)
        eleve_b = _eleve("EFF-B", StatutEleve.ACTIF)
        eleve_c = _eleve("EFF-C", StatutEleve.SUSPENDU)
        eleve_d = _eleve("EFF-D", StatutEleve.ARCHIVE)
        eleve_e = _eleve("EFF-E", StatutEleve.ACTIF)
        session.add_all([eleve_f, eleve_a, eleve_b, eleve_c, eleve_d, eleve_e])
        await session.flush()

        def _inscription(
            eleve_id: int, date_debut: date, date_fin: date | None
        ) -> InscriptionMatiere:
            return InscriptionMatiere(
                eleve_id=eleve_id,
                matiere_id=matiere.id,
                tarif_mensuel_cents=20000,
                date_debut=date_debut,
                date_fin=date_fin,
                cree_par=utilisateur_id,
            )

        session.add_all(
            [
                _inscription(eleve_f.id, date(2025, 8, 1), date(2025, 8, 31)),
                _inscription(eleve_a.id, date(2025, 9, 1), None),
                _inscription(eleve_b.id, date(2025, 9, 1), date(2025, 11, 30)),
                _inscription(eleve_c.id, date(2025, 9, 1), None),
                _inscription(eleve_d.id, date(2025, 9, 1), None),
                _inscription(eleve_e.id, date(2026, 1, 15), None),
            ]
        )
        await session.commit()

        rep = await client.get(
            "/api/dashboard/evolution-effectifs", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 200
        annees = rep.json()["annees"]
        assert len(annees) == 1
        assert annees[0]["libelle"] == "2025-2026"

        points = annees[0]["points"]
        mois_ordonnes = [p["mois"] for p in points]
        assert mois_ordonnes == [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]

        nb_par_mois = {p["mois"]: p["nb"] for p in points}
        attendu = {8: 1, 9: 3, 10: 3, 11: 3, 12: 2, 1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3}
        assert nb_par_mois == attendu

    async def test_caissier_peut_consulter_professeur_non(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier4@test.ma"
        )
        rep = await client.get(
            "/api/dashboard/evolution-effectifs",
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert rep.status_code == 200

        jeton_prof = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof2@test.ma"
        )
        rep_prof = await client.get(
            "/api/dashboard/evolution-effectifs",
            headers={"Authorization": f"Bearer {jeton_prof}"},
        )
        assert rep_prof.status_code == 403
