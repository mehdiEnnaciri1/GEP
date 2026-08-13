# GEP — Ordre de construction

Chaque étape est une **tranche verticale** : base de données → repository → service →
tests → API → écran. Une étape se termine par quelque chose d'utilisable, pas par une
couche technique isolée.

L'ordre suit les dépendances métier. Ne pas le réorganiser : le référentiel avant les
élèves, les élèves avant les paiements, les paiements avant le dashboard.

---

## Étape 0 — Fondations

Aucune valeur métier, mais tout le reste en dépend.

- `docker-compose.yml` : postgres, api, web
- Squelette FastAPI : `main.py`, configuration par `pydantic-settings`, `/health`
- `db/base.py`, `db/session.py`, mixins d'horodatage
- Alembic initialisé, première migration vide qui passe
- `core/exceptions.py` : exceptions métier et gestionnaires globaux
- `shared/money.py` et `shared/periode.py`, **avec leurs tests**
- Squelette Vite + React + Tailwind + shadcn, page blanche qui s'affiche
- `Makefile` complet
- `make lint` et `make test` verts sur un projet vide

**Critère de fin.** `make dev` démarre les trois services, `/health` répond, la page
d'accueil s'affiche, les tests passent.

Ne pas sauter les tests de `money.py`. C'est le module le plus utilisé de
l'application et le plus dangereux s'il est faux.

---

## Étape 1 — Authentification et utilisateurs

- Table `utilisateur`, enum `role_utilisateur`
- Hachage Argon2id
- Endpoints `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`
- JWT access court + refresh en cookie `httpOnly`
- `core/permissions.py` : `exige_role`
- Table `journal_audit`, service d'écriture, journalisation des connexions
- Seed : un administrateur initial
- Front : page de connexion, store de session, routes protégées, déconnexion auto
  sur 401

**Critère de fin.** Se connecter, voir une page protégée, être redirigé si non
authentifié. Un endpoint réservé à `ADMIN` renvoie 403 pour un `CAISSIER`.

Tester les permissions **dès maintenant**. Ajouter la sécurité après coup sur vingt
endpoints ne fonctionne jamais.

---

## Étape 2 — Référentiel

- `annee_scolaire`, `niveau`, `matiere`, `parametre`
- `tarif_eleve`, `tarif_professeur`
- Seed : les six niveaux du §2, les six matières du §3.2, les frais d'inscription à
  5000 centimes
- CRUD complet, réservé à `ADMIN`, `CAISSIER` en lecture
- Front : écrans de gestion, grille de saisie des tarifs (niveau × matière)

**Critère de fin.** L'administrateur crée l'année 2025-2026, saisit tous les tarifs
élève et professeur pour les couples utilisés par le centre.

La grille de tarifs est le premier écran réellement utile. Soigner l'ergonomie :
saisie en tableau, sauvegarde par ligne, pas un formulaire par tarif.

---

## Étape 3 — Élèves et inscriptions

- `eleve`, `inscription_matiere`, `frais_inscription`
- Génération du matricule (`E-2025-0001`)
- Copie du tarif dans `inscription_matiere` à la création
- Création automatique de la ligne `frais_inscription` en `NON_PAYE`
- Recherche, filtres par niveau et statut, pagination serveur
- Changement de statut avec audit
- Front : liste avec recherche, formulaire de création multi-étapes
  (identité → niveau → matières), fiche élève

**Critère de fin.** Créer un élève, lui affecter trois matières, voir son coût mensuel
total calculé, et un bandeau signalant les frais d'inscription impayés.

Vérifier ici que le tarif est bien **copié** : modifier un tarif du référentiel ne doit
pas changer le montant de l'inscription existante. C'est le test le plus important de
cette étape.

---

## Étape 4 — Paiements

Le cœur de l'application.

- `paiement`, `echeance`, `ligne_echeance`
- Idempotence (`core/idempotence.py`, en-tête `Idempotency-Key`)
- Encaissement des frais d'inscription
- Encaissement d'une mensualité, avec mise à jour de l'échéance et du statut
- Paiement partiel
- Annulation avec motif
- Numérotation des reçus (`R-2025-000123`)
- Génération des échéances : service + endpoint manuel
- Historique par élève, liste des impayés
- Front : écran de caisse (recherche élève → mois dus → encaissement), historique,
  tableau des impayés

**Critère de fin.** Encaisser un paiement partiel, voir l'échéance passer en `PARTIEL`,
compléter, la voir passer en `PAYE`. Annuler un paiement, vérifier que l'échéance
revient à son état antérieur et que la ligne annulée reste visible.

Écrire les tests d'annulation **avant** l'implémentation. La logique de recalcul du
statut d'échéance après annulation est l'endroit où les bugs se logent.

---

## Étape 5 — Professeurs et affectations

- `professeur`, `affectation`
- Contrainte d'unicité (matière, niveau, année) — voir décision D3
- Message d'erreur explicite en cas de violation : indiquer quel professeur occupe déjà
  le couple
- Compteur d'élèves par affectation, en temps réel
- Front : liste, fiche, matrice d'affectation (matières × niveaux)

**Critère de fin.** Créer M. Ahmed en mathématiques sur 1BAC et 2BAC, voir le nombre
d'élèves concernés sur chaque affectation.

---

## Étape 6 — Paie

- `paie_mensuelle`, `ligne_paie`
- Service de calcul avec **le tarif figé**
- Contrainte `CHECK` sur la cohérence arithmétique des lignes
- Génération en `BROUILLON`, validation, marquage comme payée
- Verrouillage après validation
- Lignes d'ajustement
- Front : écran de génération, détail par professeur, bordereau imprimable

**Critère de fin.** Générer la paie d'un mois, vérifier ligne à ligne contre un calcul
manuel, valider, puis constater que régénérer ne modifie rien.

Tests obligatoires : zéro élève, élève suspendu en milieu de mois, tarif modifié après
génération, tentative de régénération d'une paie validée.

Reproduire l'exemple du §7.2 comme cas de test nommé : 1BAC/Math/12 élèves = 300 DH,
2BAC/Math/15 élèves = 450 DH, total 750 DH.

---

## Étape 7 — Charges

- `categorie_charge`, `charge`
- Téléversement du justificatif (`shared/stockage.py`), validation du type MIME et de
  la taille
- Distinction `date_charge` / `periode`
- Totaux par mois et par catégorie
- Front : saisie avec dépôt de fichier, liste filtrable, aperçu du justificatif

**Critère de fin.** Enregistrer une facture d'électricité de novembre payée en décembre,
la retrouver dans les charges de novembre, ouvrir son justificatif.

Ne pas accepter n'importe quel fichier : JPEG, PNG et PDF uniquement, 5 Mo maximum,
type vérifié par les octets réels et pas par l'extension.

---

## Étape 8 — Dashboard

Toutes les données existent enfin. Les agrégats du §9 :

- Nombre d'élèves, total et par niveau
- Encaissements du mois, mensualités et inscriptions séparés
- Total des impayés
- Nombre de professeurs
- Tableau des charges par mois
- Tableau de la paie par mois
- **Bénéfice net**, selon la formule corrigée (décision D2)
- Vue restreinte pour le `CAISSIER` : ni charges, ni paie, ni bénéfice

**Critère de fin.** Chaque chiffre du dashboard est reproductible à la main à partir des
écritures. Écrire un test qui construit un jeu de données connu et vérifie les huit
indicateurs.

Le bénéfice net est le chiffre que le directeur regardera en premier. S'il est faux une
seule fois, la confiance dans l'application entière est perdue.

---

## Étape 9 — Rapports

Exports PDF et Excel du §10 :

- Liste des élèves
- Liste des paiements sur une période
- Liste des impayés
- Paie des professeurs
- Récapitulatif mensuel du centre
- Reçu de paiement individuel

Jinja2 + WeasyPrint pour le PDF, `openpyxl` pour l'Excel.

**Critère de fin.** Un PDF s'ouvre correctement, affiche les noms arabes sans caractères
manquants, et se met en page proprement sur A4.

Vérifier la police : embarquer une police couvrant l'arabe (Noto Sans Arabic) dans
l'image Docker. C'est l'oubli classique, et il ne se voit qu'à l'impression.

---

## Étape 10 — Mise en production

- Sauvegarde `pg_dump` quotidienne, rétention 30 jours, copie hors machine
- **Test de restauration effectué** — une sauvegarde jamais restaurée n'est pas une
  sauvegarde
- HTTPS
- Logs structurés, rotation
- Comptes réels créés, mots de passe changés
- Reprise des données existantes du centre, s'il y en a
- Formation : une session avec la secrétaire sur l'écran de caisse
- **Si le build (CI ou serveur) tourne derrière un proxy d'entreprise qui inspecte le
  trafic HTTPS** : le même symptôme qu'à l'étape 0 réapparaîtra
  (`CERTIFICATE_VERIFY_FAILED` pendant `pip install`, voir
  `docs/adr/2026-08-13-certificat-racine-build-docker.md`). L'exclusion côté hôte
  utilisée en développement ne s'applique pas à un environnement de build géré par un
  tiers : il faudra alors injecter le certificat racine du proxy dans `backend/Dockerfile`
  via `update-ca-certificates`, à mettre en place **avant** ce déploiement, pas
  découvert au moment du premier build qui échoue.

---

## Ce qui vient après (§12 du cahier des charges)

Groupes et horaires, pointage des présences, rappels SMS/WhatsApp, signature
électronique des reçus, application mobile.

Deux remarques sur ces évolutions. La **gestion des groupes** peut devenir prioritaire :
si le centre a deux professeurs sur un même couple (matière, niveau), elle conditionne
la justesse de la paie (voir décision D3). Les **rappels WhatsApp** nécessitent un compte
WhatsApp Business API ou un fournisseur intermédiaire, ce qui suppose un coût récurrent
et une validation par Meta — à anticiper si le besoin est réel.
