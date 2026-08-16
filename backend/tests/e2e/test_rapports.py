"""Tests e2e du module rapports — génération PDF/Excel pour chaque type de
rapport, permissions (éleves/paiements/impayés/reçu : ADMIN+CAISSIER ; paie
et récapitulatif, qui exposent charges/paie/bénéfice : ADMIN seul), et LE
test explicitement demandé : un nom d'élève en écriture arabe doit être
rendu correctement dans le PDF « liste des élèves » — pas remplacé par des
caractères manquants — grâce aux polices Noto de l'image Docker."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from httpx import AsyncClient
from pypdf import PdfReader
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
from tests.factories.professeurs import creer_affectation, creer_professeur
from tests.factories.referentiel import (
    creer_annee_scolaire,
    creer_matiere,
    creer_niveau,
    creer_tarif_professeur,
)
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


async def _construire_jeu_de_donnees(session: AsyncSession, utilisateur_id: int) -> int:
    """Construit un jeu de données couvrant les 6 rapports et retourne
    l'id d'un paiement (pour le reçu individuel)."""
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

    eleve = Eleve(
        matricule="E-2025-0001",
        nom="Alaoui",
        prenom="Yassine",
        telephone_parent="0600000000",
        niveau_code=niveau.code,
        annee_scolaire_id=annee.id,
        date_inscription=date(2025, 9, 1),
        statut=StatutEleve.ACTIF,
        cree_par=utilisateur_id,
    )
    session.add(eleve)
    await session.flush()
    session.add(
        InscriptionMatiere(
            eleve_id=eleve.id,
            matiere_id=matiere.id,
            tarif_mensuel_cents=20000,
            date_debut=date(2025, 9, 1),
            cree_par=utilisateur_id,
        )
    )

    paiement = Paiement(
        numero_recu="R-2025-000001",
        eleve_id=eleve.id,
        type=TypePaiement.MENSUALITE,
        periode=PERIODE,
        montant_cents=20000,
        date_paiement=date(2025, 10, 5),
        mode=ModePaiement.VIREMENT,
        cree_par=utilisateur_id,
    )
    session.add(paiement)
    session.add(
        Echeance(
            eleve_id=eleve.id,
            periode=PERIODE,
            montant_du_cents=20000,
            montant_paye_cents=20000,
            statut=StatutEcheance.PAYE,
        )
    )
    session.add(
        Echeance(
            eleve_id=eleve.id,
            periode="2025-11",
            montant_du_cents=20000,
            montant_paye_cents=0,
            statut=StatutEcheance.NON_PAYE,
        )
    )

    categorie = CategorieCharge(libelle="Loyer")
    session.add(categorie)
    await session.flush()
    session.add(
        Charge(
            categorie_id=categorie.id,
            description="Loyer octobre",
            montant_cents=300000,
            date_charge=date(2025, 10, 1),
            periode=PERIODE,
            mode_paiement=ModePaiement.VIREMENT,
            cree_par=utilisateur_id,
        )
    )
    session.add(
        PaieMensuelle(
            professeur_id=professeur.id,
            periode=PERIODE,
            total_cents=12000,
            statut=StatutPaie.VALIDEE,
        )
    )
    await session.commit()
    await session.refresh(paiement)
    return paiement.id


class TestRapportsAdminEtCaissier:
    """Élèves, paiements, impayés, reçu : ADMIN et CAISSIER."""

    async def test_liste_eleves_pdf_et_excel(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        pdf = await client.get("/api/rapports/eleves/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")

        excel = await client.get("/api/rapports/eleves/excel", headers=headers)
        assert excel.status_code == 200
        assert (
            excel.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(excel.content) > 0

    async def test_paiements_pdf_et_excel(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        pdf = await client.get(f"/api/rapports/paiements/pdf?periode={PERIODE}", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        excel = await client.get(
            f"/api/rapports/paiements/excel?periode={PERIODE}", headers=headers
        )
        assert excel.status_code == 200

    async def test_impayes_pdf_et_excel(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        pdf = await client.get("/api/rapports/impayes/pdf?periode=2025-11", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        excel = await client.get("/api/rapports/impayes/excel?periode=2025-11", headers=headers)
        assert excel.status_code == 200

    async def test_recu_pdf(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        paiement_id = await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        rep = await client.get(f"/api/rapports/recu/{paiement_id}/pdf", headers=headers)
        assert rep.status_code == 200
        assert rep.content.startswith(b"%PDF")

    async def test_recu_paiement_introuvable(self, client: AsyncClient, session: AsyncSession):
        jeton, _ = await _jeton_admin(client, session)
        rep = await client.get(
            "/api/rapports/recu/999999/pdf", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 404

    async def test_caissier_peut_generer_eleves_et_recu(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton_admin, utilisateur_id = await _jeton_admin(client, session)
        paiement_id = await _construire_jeu_de_donnees(session, utilisateur_id)

        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier1@test.ma"
        )
        headers = {"Authorization": f"Bearer {jeton}"}

        assert (await client.get("/api/rapports/eleves/pdf", headers=headers)).status_code == 200
        assert (
            await client.get(f"/api/rapports/recu/{paiement_id}/pdf", headers=headers)
        ).status_code == 200

    async def test_professeur_refuse(self, client: AsyncClient, session: AsyncSession):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.PROFESSEUR, email="prof1@test.ma"
        )
        rep = await client.get(
            "/api/rapports/eleves/pdf", headers={"Authorization": f"Bearer {jeton}"}
        )
        assert rep.status_code == 403

    async def test_sans_jeton(self, client: AsyncClient):
        rep = await client.get("/api/rapports/eleves/pdf")
        assert rep.status_code == 401


class TestRapportsAdminSeul:
    """Paie et récapitulatif mensuel (charges/paie/bénéfice) : ADMIN seul."""

    async def test_paie_pdf_et_excel(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        pdf = await client.get(f"/api/rapports/paie/pdf?periode={PERIODE}", headers=headers)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        excel = await client.get(f"/api/rapports/paie/excel?periode={PERIODE}", headers=headers)
        assert excel.status_code == 200

    async def test_recapitulatif_pdf_et_excel(self, client: AsyncClient, session: AsyncSession):
        jeton, utilisateur_id = await _jeton_admin(client, session)
        await _construire_jeu_de_donnees(session, utilisateur_id)
        headers = {"Authorization": f"Bearer {jeton}"}

        pdf = await client.get(
            f"/api/rapports/recapitulatif/pdf?periode={PERIODE}", headers=headers
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        excel = await client.get(
            f"/api/rapports/recapitulatif/excel?periode={PERIODE}", headers=headers
        )
        assert excel.status_code == 200

    async def test_caissier_ne_peut_pas_generer_la_paie(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier2@test.ma"
        )
        rep = await client.get(
            f"/api/rapports/paie/pdf?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403

    async def test_caissier_ne_peut_pas_generer_le_recapitulatif(
        self, client: AsyncClient, session: AsyncSession
    ):
        jeton = await _jeton(
            client, session, role=RoleUtilisateur.CAISSIER, email="caissier3@test.ma"
        )
        rep = await client.get(
            f"/api/rapports/recapitulatif/pdf?periode={PERIODE}",
            headers={"Authorization": f"Bearer {jeton}"},
        )
        assert rep.status_code == 403


class TestRenduArabe:
    async def test_nom_arabe_rendu_dans_le_pdf_liste_eleves(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Le point explicitement demandé : les polices Noto de l'image
        Docker (fonts-noto-core, voir Dockerfile) doivent rendre un nom
        d'élève écrit en arabe — pas un rectangle de caractère manquant.
        Vérifié en extrayant le texte du PDF généré : si la police ne
        couvrait pas le script arabe, WeasyPrint substituerait des glyphes
        de remplacement et le texte arabe n'apparaîtrait pas tel quel."""
        jeton, utilisateur_id = await _jeton_admin(client, session)
        headers = {"Authorization": f"Bearer {jeton}"}

        annee = await creer_annee_scolaire(session)
        niveau = await creer_niveau(session)

        nom_arabe = "العلوي"
        prenom_arabe = "يوسف"
        session.add(
            Eleve(
                matricule="E-2025-ARABE",
                nom=nom_arabe,
                prenom=prenom_arabe,
                telephone_parent="0600000000",
                niveau_code=niveau.code,
                annee_scolaire_id=annee.id,
                date_inscription=date(2025, 9, 1),
                statut=StatutEleve.ACTIF,
                cree_par=utilisateur_id,
            )
        )
        await session.commit()

        rep = await client.get("/api/rapports/eleves/pdf", headers=headers)
        assert rep.status_code == 200
        assert rep.content.startswith(b"%PDF")

        texte = ""
        lecteur = PdfReader(BytesIO(rep.content))
        for page in lecteur.pages:
            texte += page.extract_text()

        assert nom_arabe in texte
        assert prenom_arabe in texte
