"""Tests e2e du module paie — écrits AVANT le service (voir CLAUDE.md,
méthode de travail attendue). Couvrent au minimum : zéro élève sur une
affectation, élève suspendu en milieu de mois, matière ajoutée en cours de
mois, tarif modifié après génération (ne doit rien changer), tentative de
régénération d'une paie VALIDEE (refusée), l'exemple nommé du §7.2 du cahier
des charges, et la décision D4 (paie toujours sur les inscrits, jamais sur
le statut de paiement)."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RoleUtilisateur
from app.modules.eleves.models import Eleve, InscriptionMatiere, StatutEleve
from tests.factories.professeurs import creer_affectation, creer_professeur
from tests.factories.referentiel import (
    creer_annee_scolaire,
    creer_matiere,
    creer_niveau,
    creer_tarif_professeur,
)
from tests.factories.utilisateur import MOT_DE_PASSE_TEST, construire_utilisateur

PERIODE = "2025-10"


async def _jeton_admin(
    client: AsyncClient, session: AsyncSession, *, email: str = "admin@test.ma"
) -> tuple[str, int]:
    utilisateur = await construire_utilisateur(session, email=email, role=RoleUtilisateur.ADMIN)
    session.add(utilisateur)
    await session.commit()
    await session.refresh(utilisateur)

    reponse = await client.post(
        "/api/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE_TEST}
    )
    assert reponse.status_code == 200
    return str(reponse.json()["access_token"]), utilisateur.id


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


async def _creer_eleve(
    session: AsyncSession,
    *,
    utilisateur_id: int,
    niveau_code: str,
    annee_scolaire_id: int,
    matiere_id: int,
    matricule: str,
    statut: StatutEleve = StatutEleve.ACTIF,
    date_debut_inscription: date = date(2025, 9, 1),
    date_fin_inscription: date | None = None,
) -> Eleve:
    eleve = Eleve(
        matricule=matricule,
        nom="Eleve",
        prenom=matricule,
        telephone_parent="0600000000",
        niveau_code=niveau_code,
        annee_scolaire_id=annee_scolaire_id,
        date_inscription=date(2025, 9, 1),
        statut=statut,
        cree_par=utilisateur_id,
    )
    session.add(eleve)
    await session.flush()
    session.add(
        InscriptionMatiere(
            eleve_id=eleve.id,
            matiere_id=matiere_id,
            tarif_mensuel_cents=0,
            date_debut=date_debut_inscription,
            date_fin=date_fin_inscription,
            cree_par=utilisateur_id,
        )
    )
    await session.commit()
    await session.refresh(eleve)
    return eleve


class TestGenerationPaie:
    async def test_exemple_nomme_du_cahier_des_charges(
        self, client: AsyncClient, session: AsyncSession
    ):
        """§7.2 : 1BAC/Math/12 élèves = 300 DH, 2BAC/Math/15 élèves = 450 DH,
        total 750 DH."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau_1bac = await creer_niveau(session, code="1BAC", ordre=5)
        niveau_2bac = await creer_niveau(session, code="2BAC", ordre=6)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)

        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau_1bac.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau_2bac.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=3000,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau_1bac.code,
            annee_scolaire_id=annee.id,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau_2bac.code,
            annee_scolaire_id=annee.id,
        )

        for i in range(12):
            await _creer_eleve(
                session,
                utilisateur_id=utilisateur_id,
                niveau_code=niveau_1bac.code,
                annee_scolaire_id=annee.id,
                matiere_id=matiere.id,
                matricule=f"1BAC-{i}",
            )
        for i in range(15):
            await _creer_eleve(
                session,
                utilisateur_id=utilisateur_id,
                niveau_code=niveau_2bac.code,
                annee_scolaire_id=annee.id,
                matiere_id=matiere.id,
                matricule=f"2BAC-{i}",
            )

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.status_code == 200
        assert rep.json()["nombre_generees"] == 1

        paies = await client.get(f"/api/paie?periode={PERIODE}", headers=headers)
        assert len(paies.json()) == 1
        paie_id = paies.json()[0]["id"]
        assert paies.json()[0]["total_cents"] == 75000

        detail = await client.get(f"/api/paie/{paie_id}", headers=headers)
        lignes = {
            (ligne["niveau_code"], ligne["matiere_id"]): ligne for ligne in detail.json()["lignes"]
        }
        assert lignes[(niveau_1bac.code, matiere.id)]["nombre_eleves"] == 12
        assert lignes[(niveau_1bac.code, matiere.id)]["montant_cents"] == 30000
        assert lignes[(niveau_2bac.code, matiere.id)]["nombre_eleves"] == 15
        assert lignes[(niveau_2bac.code, matiere.id)]["montant_cents"] == 45000

    async def test_zero_eleve_sur_une_affectation(self, client: AsyncClient, session: AsyncSession):
        jeton, _ = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.json()["nombre_generees"] == 1

        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        assert paies[0]["total_cents"] == 0

        detail = await client.get(f"/api/paie/{paies[0]['id']}", headers=headers)
        assert detail.json()["lignes"][0]["nombre_eleves"] == 0
        assert detail.json()["lignes"][0]["montant_cents"] == 0

    async def test_eleve_suspendu_en_milieu_de_mois_exclu(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        actif = await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="ACTIF-1",
        )
        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="SUSPENDU-1",
            statut=StatutEleve.SUSPENDU,
        )

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.json()["nombre_generees"] == 1
        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        assert paies[0]["total_cents"] == 2500

        detail = await client.get(f"/api/paie/{paies[0]['id']}", headers=headers)
        assert detail.json()["lignes"][0]["nombre_eleves"] == 1
        assert actif.statut == StatutEleve.ACTIF

    async def test_matiere_ajoutee_en_cours_de_mois_compte_le_mois_entier(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        # Inscription qui commence le 20 du mois de la période — pas de
        # prorata (même principe que la décision D6 pour les échéances) :
        # le mois complet est dû/compté dès lors que l'inscription chevauche
        # la période.
        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="MILIEU-MOIS",
            date_debut_inscription=date(2025, 10, 20),
        )

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.json()["nombre_generees"] == 1
        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        assert paies[0]["total_cents"] == 2500

    async def test_tarif_modifie_apres_generation_ne_change_rien(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        tarif = await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="ELEVE-1",
        )

        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]

        tarif.montant_par_eleve_cents = 999999
        session.add(tarif)
        await session.commit()

        detail = await client.get(f"/api/paie/{paie_id}", headers=headers)
        assert detail.json()["lignes"][0]["tarif_unitaire_cents"] == 2500
        assert detail.json()["lignes"][0]["montant_cents"] == 2500
        assert detail.json()["total_cents"] == 2500

    async def test_regeneration_paie_validee_ignoree_silencieusement(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Régénérer une période où la seule paie existante est déjà VALIDEE
        ne doit ni la toucher, ni faire échouer l'appel : elle est ignorée,
        `nombre_generees` retombe à 0 (voir CLAUDE.md — verrouillage)."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]

        valider = await client.post(f"/api/paie/{paie_id}/valider", headers=headers)
        assert valider.status_code == 200
        assert valider.json()["statut"] == "VALIDEE"

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.status_code == 200
        assert rep.json()["nombre_generees"] == 0

        detail = await client.get(f"/api/paie/{paie_id}", headers=headers)
        assert detail.json()["statut"] == "VALIDEE"

    async def test_generation_partielle_ne_touche_pas_les_paies_verrouillees(
        self, client: AsyncClient, session: AsyncSession
    ):
        """L'admin valide au fil de l'eau : dès qu'un professeur est validé
        pour la période, régénérer ne doit pas empêcher de générer/régénérer
        les autres professeurs encore en brouillon."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        # Deux niveaux distincts : le couple (année, matière, niveau) est
        # unique par professeur (décision D3) — les deux affectations de ce
        # test ne peuvent pas partager le même niveau.
        niveau_valide = await creer_niveau(session, code="1BAC", ordre=5)
        niveau_brouillon = await creer_niveau(session, code="2BAC", ordre=6)
        matiere = await creer_matiere(session)
        professeur_valide = await creer_professeur(session, nom="Valide", prenom="Prof")
        professeur_brouillon = await creer_professeur(session, nom="Brouillon", prenom="Prof")
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau_valide.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau_brouillon.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_affectation(
            session,
            professeur_id=professeur_valide.id,
            matiere_id=matiere.id,
            niveau_code=niveau_valide.code,
            annee_scolaire_id=annee.id,
        )
        await creer_affectation(
            session,
            professeur_id=professeur_brouillon.id,
            matiere_id=matiere.id,
            niveau_code=niveau_brouillon.code,
            annee_scolaire_id=annee.id,
        )
        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau_valide.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="ELEVE-PARTIEL",
        )

        premiere = await client.post(
            "/api/paie/generer", json={"periode": PERIODE}, headers=headers
        )
        assert premiere.json()["nombre_generees"] == 2

        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        paie_validee = next(p for p in paies if p["professeur_id"] == professeur_valide.id)
        await client.post(f"/api/paie/{paie_validee['id']}/valider", headers=headers)

        seconde = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert seconde.status_code == 200
        assert seconde.json()["nombre_generees"] == 1

        paies_apres = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        statut_valide = next(p for p in paies_apres if p["professeur_id"] == professeur_valide.id)[
            "statut"
        ]
        statut_brouillon = next(
            p for p in paies_apres if p["professeur_id"] == professeur_brouillon.id
        )["statut"]
        assert statut_valide == "VALIDEE"
        assert statut_brouillon == "BROUILLON"

    async def test_base_calcul_paie_toujours_sur_les_inscrits(
        self, client: AsyncClient, session: AsyncSession
    ):
        """D4 : un élève inscrit mais dont l'échéance du mois n'est pas payée
        compte quand même dans la paie du professeur — le calcul ne dépend
        jamais du statut de paiement."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere.id,
            montant_par_eleve_cents=2500,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        # Aucune échéance générée pour cet élève : impayé de fait.
        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere.id,
            matricule="IMPAYE-1",
        )

        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        assert paies[0]["total_cents"] == 2500

    async def test_eleve_pack_compte_dans_chaque_matiere_du_niveau(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Test obligatoire : le pack désigne littéralement toutes les
        matières du niveau — un élève pack a une inscription réelle par
        matière, donc compte normalement dans CHAQUE affectation de ce
        niveau, sans règle spéciale côté paie (voir
        docs/adr/2026-08-29-pack-et-reduction.md)."""
        jeton, utilisateur_id = await _jeton_admin(client, session, email="pack_paie1@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session, code="2BAC", ordre=6)
        matiere_maths = await creer_matiere(session, code="MATH", libelle="Maths")
        matiere_physique = await creer_matiere(session, code="PHYSIQUE", libelle="Physique")
        professeur = await creer_professeur(session)

        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_maths.id,
            montant_par_eleve_cents=3000,
        )
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_physique.id,
            montant_par_eleve_cents=2000,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_maths.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_physique.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        eleve = Eleve(
            matricule="PACK-1",
            nom="Eleve",
            prenom="Pack",
            telephone_parent="0600000000",
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            date_inscription=date(2025, 9, 1),
            statut=StatutEleve.ACTIF,
            est_pack=True,
            cree_par=utilisateur_id,
        )
        session.add(eleve)
        await session.flush()
        session.add_all(
            [
                InscriptionMatiere(
                    eleve_id=eleve.id,
                    matiere_id=matiere_maths.id,
                    tarif_mensuel_cents=22500,
                    date_debut=date(2025, 9, 1),
                    cree_par=utilisateur_id,
                ),
                InscriptionMatiere(
                    eleve_id=eleve.id,
                    matiere_id=matiere_physique.id,
                    tarif_mensuel_cents=22500,
                    date_debut=date(2025, 9, 1),
                    cree_par=utilisateur_id,
                ),
            ]
        )
        await session.commit()

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.status_code == 200

        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        paie_id = paies[0]["id"]
        detail = await client.get(f"/api/paie/{paie_id}", headers=headers)
        lignes = {
            (ligne["niveau_code"], ligne["matiere_id"]): ligne for ligne in detail.json()["lignes"]
        }
        assert lignes[(niveau.code, matiere_maths.id)]["nombre_eleves"] == 1
        assert lignes[(niveau.code, matiere_physique.id)]["nombre_eleves"] == 1

    async def test_deux_eleves_pack_et_individuel_comptent_ensemble(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Test obligatoire : deux élèves sur (Maths, 1BAC), un pack et un
        individuel — nombre_eleves = 2, montant = 2 × tarif_prof."""
        jeton, utilisateur_id = await _jeton_admin(client, session, email="pack_paie2@test.ma")
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session, code="1BAC", ordre=5)
        matiere_maths = await creer_matiere(session, code="MATH", libelle="Maths")
        matiere_svt = await creer_matiere(session, code="SVT", libelle="SVT")
        professeur = await creer_professeur(session)

        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_maths.id,
            montant_par_eleve_cents=3000,
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere_maths.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        await _creer_eleve(
            session,
            utilisateur_id=utilisateur_id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            matiere_id=matiere_maths.id,
            matricule="IND-1",
        )

        eleve_pack = Eleve(
            matricule="PACK-2",
            nom="Eleve",
            prenom="Pack",
            telephone_parent="0600000000",
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
            date_inscription=date(2025, 9, 1),
            statut=StatutEleve.ACTIF,
            est_pack=True,
            cree_par=utilisateur_id,
        )
        session.add(eleve_pack)
        await session.flush()
        session.add_all(
            [
                InscriptionMatiere(
                    eleve_id=eleve_pack.id,
                    matiere_id=matiere_maths.id,
                    tarif_mensuel_cents=22500,
                    date_debut=date(2025, 9, 1),
                    cree_par=utilisateur_id,
                ),
                InscriptionMatiere(
                    eleve_id=eleve_pack.id,
                    matiere_id=matiere_svt.id,
                    tarif_mensuel_cents=22500,
                    date_debut=date(2025, 9, 1),
                    cree_par=utilisateur_id,
                ),
            ]
        )
        await session.commit()

        rep = await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        assert rep.status_code == 200

        paies = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()
        paie_id = paies[0]["id"]
        detail = await client.get(f"/api/paie/{paie_id}", headers=headers)
        ligne = next(
            ligne
            for ligne in detail.json()["lignes"]
            if ligne["niveau_code"] == niveau.code and ligne["matiere_id"] == matiere_maths.id
        )
        assert ligne["nombre_eleves"] == 2
        assert ligne["montant_cents"] == 6000

    async def test_caissier_ne_peut_pas_generer(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        rep = await client.post(
            "/api/paie/generer",
            json={"periode": PERIODE},
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.post("/api/paie/generer", json={"periode": PERIODE})
        assert rep.status_code == 401


class TestValidationEtPaiement:
    async def test_marquer_payee_avant_validation_refuse(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, _ = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]

        rep = await client.post(
            f"/api/paie/{paie_id}/marquer-payee",
            json={"date_paiement": "2025-11-05", "mode_paiement": "VIREMENT"},
            headers=headers,
        )
        assert rep.status_code == 409

    async def test_valider_puis_marquer_payee(self, client: AsyncClient, session: AsyncSession):
        jeton, _ = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]

        await client.post(f"/api/paie/{paie_id}/valider", headers=headers)
        rep = await client.post(
            f"/api/paie/{paie_id}/marquer-payee",
            json={"date_paiement": "2025-11-05", "mode_paiement": "VIREMENT"},
            headers=headers,
        )
        assert rep.status_code == 200
        assert rep.json()["statut"] == "PAYEE"
        assert rep.json()["mode_paiement"] == "VIREMENT"

    async def test_caissier_ne_peut_pas_valider(self, client: AsyncClient, session: AsyncSession):
        jeton_admin, _ = await _jeton_admin(client, session, email="admin2@test.ma")
        headers_admin = {"Authorization": f"Bearer {jeton_admin}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers_admin)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers_admin)).json()[
            0
        ]["id"]

        jeton_caissier = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.post(
            f"/api/paie/{paie_id}/valider",
            headers={"Authorization": f"Bearer {jeton_caissier}"},
        )
        assert rep.status_code == 403

    async def test_caissier_ne_peut_pas_lister(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.get(
            f"/api/paie?periode={PERIODE}", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get(f"/api/paie?periode={PERIODE}")
        assert rep.status_code == 401


class TestAjustement:
    async def test_ajustement_sur_paie_validee_refuse(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Le verrou de la paie (CLAUDE.md) s'applique aussi à l'ajustement :
        une paie VALIDEE ou PAYEE ne doit plus jamais voir son total_cents
        bouger, même via une ligne d'ajustement — la régularisation se fait
        sur la période SUIVANTE (voir test_ajustement_nominal_sur_periode_suivante)."""
        jeton, _ = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]
        await client.post(f"/api/paie/{paie_id}/valider", headers=headers)

        rep = await client.post(
            "/api/paie/ajustement",
            json={
                "professeur_id": professeur.id,
                "periode": PERIODE,
                "matiere_id": matiere.id,
                "niveau_code": niveau.code,
                "montant_cents": 5000,
                "motif": "Oubli d'un élève lors de la génération",
            },
            headers=headers,
        )
        assert rep.status_code == 409

        paie = (await client.get(f"/api/paie/{paie_id}", headers=headers)).json()
        assert paie["total_cents"] == 0
        assert not any(ligne["est_ajustement"] for ligne in paie["lignes"])

    async def test_ajustement_nominal_sur_periode_suivante(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Cas nominal : la régularisation d'une paie VALIDEE de {PERIODE}
        est portée sur la paie (BROUILLON) de la période suivante."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        matiere = await creer_matiere(session)
        professeur = await creer_professeur(session)
        await creer_tarif_professeur(
            session, annee_scolaire_id=annee.id, niveau_code=niveau.code, matiere_id=matiere.id
        )
        await creer_affectation(
            session,
            professeur_id=professeur.id,
            matiere_id=matiere.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )

        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers)
        paie_id = (await client.get(f"/api/paie?periode={PERIODE}", headers=headers)).json()[0][
            "id"
        ]
        await client.post(f"/api/paie/{paie_id}/valider", headers=headers)

        periode_suivante = "2025-11"
        # La paie de la période suivante doit exister (en BROUILLON) avant
        # de pouvoir y porter l'ajustement — générée normalement le mois
        # suivant, ici on la génère explicitement pour le test.
        await client.post("/api/paie/generer", json={"periode": periode_suivante}, headers=headers)

        rep = await client.post(
            "/api/paie/ajustement",
            json={
                "professeur_id": professeur.id,
                "periode": periode_suivante,
                "matiere_id": matiere.id,
                "niveau_code": niveau.code,
                "montant_cents": 5000,
                "motif": "Oubli d'un élève sur la paie de " + PERIODE,
            },
            headers=headers,
        )
        assert rep.status_code == 201
        assert rep.json()["est_ajustement"] is True

        paie_periode = (await client.get(f"/api/paie/{paie_id}", headers=headers)).json()
        assert paie_periode["total_cents"] == 0

        paies_suivantes = (
            await client.get(f"/api/paie?periode={periode_suivante}", headers=headers)
        ).json()
        paie_suivante_id = paies_suivantes[0]["id"]
        paie_suivante = (await client.get(f"/api/paie/{paie_suivante_id}", headers=headers)).json()
        assert paie_suivante["total_cents"] == 5000

    async def test_professeur_introuvable_sans_paie_pour_la_periode(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton, _ = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}
        professeur = await creer_professeur(session)
        matiere = await creer_matiere(session)
        niveau = await creer_niveau(session)

        rep = await client.post(
            "/api/paie/ajustement",
            json={
                "professeur_id": professeur.id,
                "periode": PERIODE,
                "matiere_id": matiere.id,
                "niveau_code": niveau.code,
                "montant_cents": 5000,
                "motif": "Correction",
            },
            headers=headers,
        )
        assert rep.status_code == 404

    async def test_caissier_ne_peut_pas_ajuster(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier4@test.ma"
        )
        rep = await client.post(
            "/api/paie/ajustement",
            json={
                "professeur_id": 1,
                "periode": PERIODE,
                "matiere_id": 1,
                "niveau_code": "1BAC",
                "montant_cents": 5000,
                "motif": "Correction",
            },
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403


class TestMesPaies:
    async def test_professeur_consulte_sa_paie_et_pas_celle_dun_autre(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton_admin, _ = await _jeton_admin(client, session, email="admin3@test.ma")
        headers_admin = {"Authorization": f"Bearer {jeton_admin}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)
        # Deux matières distinctes : le couple (année, matière, niveau) est
        # unique par professeur (décision D3).
        matiere_mon_prof = await creer_matiere(session, code="MATH", libelle="Mathématiques")
        matiere_autre_prof = await creer_matiere(session, code="PHYSIQUE", libelle="Physique")
        mon_professeur = await creer_professeur(session, nom="Alaoui", prenom="Karim")
        autre_professeur = await creer_professeur(session, nom="Bennani", prenom="Yassine")
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_mon_prof.id,
        )
        await creer_tarif_professeur(
            session,
            annee_scolaire_id=annee.id,
            niveau_code=niveau.code,
            matiere_id=matiere_autre_prof.id,
        )
        await creer_affectation(
            session,
            professeur_id=mon_professeur.id,
            matiere_id=matiere_mon_prof.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await creer_affectation(
            session,
            professeur_id=autre_professeur.id,
            matiere_id=matiere_autre_prof.id,
            niveau_code=niveau.code,
            annee_scolaire_id=annee.id,
        )
        await client.post("/api/paie/generer", json={"periode": PERIODE}, headers=headers_admin)

        jeton_prof = await _jeton(
            client,
            session,
            role=RoleUtilisateur.PROFESSEUR,
            email="prof1@test.ma",
            professeur_id=mon_professeur.id,
        )
        rep = await client.get(
            "/api/paie/mes-paies", headers={"Authorization": f"Bearer {jeton_prof}"}
        )
        assert rep.status_code == 200
        paies = rep.json()
        assert len(paies) == 1
        assert paies[0]["professeur_id"] == mon_professeur.id
        assert all(p["professeur_id"] != autre_professeur.id for p in paies)

    async def test_caissier_ne_peut_pas_consulter_mes_paies(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier5@test.ma"
        )
        rep = await client.get("/api/paie/mes-paies", headers={"Authorization": f"Bearer {jeton}"})
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get("/api/paie/mes-paies")
        assert rep.status_code == 401
