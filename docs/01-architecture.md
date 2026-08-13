# GEP — Architecture technique

**Gestion des Élèves et des Paiements** — Centre de soutien scolaire
Version 1.0 — document de référence

---

## 1. Contraintes qui dictent l'architecture

Avant les choix techniques, les faits qui les justifient.

| Contrainte | Valeur estimée | Conséquence |
|---|---|---|
| Nombre d'élèves | 100 à 500 | Aucun besoin de scalabilité horizontale |
| Nombre de professeurs | 10 à 30 | Tables minuscules |
| Utilisateurs simultanés | 1 à 3 | Un seul processus applicatif suffit |
| Volume de paiements / mois | ~500 lignes | Postgres traite ça sans indexation exotique |
| Criticité des données | **Très haute** | Argent réel, paie réelle. Audit et sauvegardes non négociables |
| Équipe | 1 développeur | Simplicité opérationnelle prioritaire sur l'élégance distribuée |
| Connectivité | Réseau local ou petit VPS | Déploiement mono-machine |

La conclusion : **ce projet est petit en volume et critique en exactitude**. Toute la rigueur doit aller dans la justesse des calculs, l'immuabilité des écritures et la traçabilité — pas dans l'infrastructure.

---

## 2. Stack retenue

### Backend

| Composant | Choix | Justification |
|---|---|---|
| Langage | Python 3.12 | |
| Framework | FastAPI | OpenAPI natif, validation Pydantic, async |
| Validation | Pydantic v2 | Contrats d'API stricts |
| ORM | SQLAlchemy 2.0 (mode async) | Requêtes typées, contrôle transactionnel fin |
| Migrations | Alembic | Historique de schéma versionné — obligatoire |
| Base de données | PostgreSQL 16 | Transactions ACID, `NUMERIC` exact, contraintes `CHECK`, `jsonb` pour l'audit |
| Auth | JWT (access court + refresh) | Cookie `httpOnly`, `SameSite=Strict` |
| Hash | Argon2id (`argon2-cffi`) | Standard actuel, pas bcrypt |
| Export Excel | `openpyxl` | Écriture de classeurs formatés |
| Export PDF | Jinja2 + WeasyPrint | Templates HTML → PDF, gère l'UTF-8 et l'arabe |
| Tâches planifiées | APScheduler, en processus | Une seule tâche mensuelle. Pas de Celery |
| Tests | pytest + httpx + testcontainers | |

> **WeasyPrint est un extra optionnel (`pip install -e ".[pdf]"`), et sa génération
> de PDF n'est garantie qu'en Linux/Docker.** La bibliothèque dépend de Pango,
> Cairo, GDK-Pixbuf, HarfBuzz et Fribidi natifs, absents d'un poste Windows sans
> installation manuelle du runtime GTK. L'image Docker du backend (Debian
> bookworm) installe ces bibliothèques système ; un venv local hors conteneur
> peut développer tous les modules sauf `rapports/pdf.py`, qui importe
> `weasyprint` en paresseux pour ne pas faire échouer les autres modules à
> l'import. Voir `docs/adr/2026-08-13-weasyprint-extra-optionnel.md`.

### Frontend

| Composant | Choix | Justification |
|---|---|---|
| Framework | React 19 + TypeScript | |
| Build | Vite | Démarrage instantané, build statique |
| Routage | React Router 7 (mode déclaratif, pas le mode framework) | Voir `docs/adr/2026-08-13-react-19-react-router-7.md` |
| Données serveur | TanStack Query | Cache, invalidation, états de chargement |
| Tableaux | TanStack Table | Tri, filtre, pagination côté serveur |
| Formulaires | React Hook Form + Zod | Validation miroir de Pydantic |
| Styles | Tailwind CSS | |
| Composants | shadcn/ui | Code copié dans le projet, pas une dépendance opaque |
| Graphiques | Recharts | Dashboard |
| Client API | **Généré** via `openapi-typescript` | Voir §5 |

### Ce que je n'utilise pas, et pourquoi

**Pas de Redis.** Il servirait au cache, aux sessions et de broker. Le cache est inutile sur des tables de 500 lignes ; les sessions sont dans le JWT ; il n'y a pas de file de tâches. C'est un service de plus à sauvegarder et à superviser pour rien.

**Pas de MinIO / S3.** Les seuls fichiers sont les justificatifs de charges — quelques dizaines de photos par an. Un volume Docker monté sur disque, inclus dans la sauvegarde, suffit. L'accès passe par une abstraction `StockageFichiers` pour qu'un basculement vers S3 reste possible sans toucher au métier.

**Pas de Celery / ARQ.** La génération des échéances mensuelles et de la paie sont deux tâches par mois, sur quelques centaines de lignes, en moins d'une seconde. APScheduler en processus fait le travail, et les deux tâches sont aussi déclenchables manuellement depuis l'interface — ce qui est de toute façon nécessaire.

**Pas de microservices.** Un seul développeur, un domaine cohérent, des transactions qui doivent être atomiques (un paiement touche `paiement` et `echeance` ensemble). Un monolithe modulaire, découpé proprement, est le bon choix ici et le restera.

**Pas de Next.js.** Application intégralement derrière authentification, aucun besoin de SEO. Un SPA statique évite d'exploiter un second runtime Node à côté de FastAPI et empêche la logique métier de se disperser sur deux langages.

---

## 3. Style architectural : monolithe modulaire en couches

### Les quatre couches

Chaque module métier est découpé identiquement, du plus stable au plus volatil :

```
router.py       HTTP        Validation d'entrée, codes de statut, dépendances, permissions
service.py      Métier      Règles, orchestration, frontière transactionnelle
repository.py   Persistance Requêtes SQLAlchemy, aucune règle métier
models.py       Schéma      Tables SQLAlchemy
schemas.py      Contrats    Pydantic — entrée et sortie
```

### Les deux règles qui font tenir l'ensemble

**Le service ignore HTTP.** Aucun `HTTPException`, aucun objet `Request`, aucun code de statut dans un service. Il lève des exceptions métier (`EleveIntrouvable`, `PaieDejaValidee`, `MontantInvalide`) qu'un gestionnaire global traduit en réponses HTTP. Conséquence : les services sont testables sans client HTTP, et réutilisables par les tâches planifiées et les exports.

**Le repository ignore le métier.** Il expose `get_by_id`, `list_paginated`, `count_eleves_par_matiere_niveau`. Il ne décide jamais si une opération est permise.

### La frontière transactionnelle est le service

Une méthode de service = une transaction. Le router ouvre la session, le service la reçoit et la valide ou l'annule en bloc. Enregistrer un paiement écrit dans `paiement`, met à jour `echeance` et insère dans `journal_audit` — les trois réussissent ou aucune n'a lieu.

---

## 4. Découpage en modules

```
auth           Utilisateurs, connexion, JWT, rôles, permissions
referentiel    Niveaux, matières, tarifs élève, tarifs professeur,
               catégories de charges, paramètres, années scolaires
eleves         Élèves, inscriptions aux matières
paiements      Frais d'inscription, échéances mensuelles, paiements, annulations
professeurs    Professeurs, affectations (matière × niveau)
paie           Génération, validation et clôture de la paie mensuelle
charges        Charges du centre, justificatifs
dashboard      Agrégats et indicateurs
rapports       Exports PDF et Excel
audit          Journal d'audit (transversal, écrit par les autres modules)
```

Le graphe de dépendances est acyclique et descendant :

```
        auth
          │
    referentiel
       ╱      ╲
  eleves    professeurs
     │           │
 paiements     paie
       ╲       ╱
        ╲     ╱   charges
         ╲   ╱   ╱
        dashboard
             │
         rapports
```

`audit` est appelé par tous et n'appelle personne. **Aucun import remontant** : `referentiel` n'importe jamais `eleves`. Si le besoin apparaît, c'est le signe que la responsabilité est mal placée.

---

## 5. Le contrat API est généré, jamais écrit à la main

FastAPI expose `/openapi.json`. Une commande régénère le client TypeScript :

```bash
make api-types   # openapi-typescript → frontend/src/api/generated/schema.d.ts
```

Le fichier généré est commité mais **jamais édité**. Conséquence directe : si un schéma Pydantic change côté backend et que le front n'est pas mis à jour, `tsc` échoue à la compilation. La désynchronisation front/back — première source de bugs sur ce type de projet — devient impossible à ignorer.

Les dossiers `backend/app/modules/` et `frontend/src/features/` portent les **mêmes noms**. Quand une modification touche les paiements, les deux emplacements concernés sont évidents, pour toi comme pour Claude Code.

---

## 6. Points transversaux critiques

### 6.1 Représentation de l'argent

**Tous les montants sont des entiers en centimes, en `BIGINT`.**

```python
montant_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
```

Jamais de `float`, jamais de `REAL`, jamais de `DOUBLE PRECISION`. Une erreur d'arrondi sur un montant est irréparable en production et indétectable pendant des mois.

La conversion en dirhams n'a lieu qu'à deux endroits : à l'affichage (`Intl.NumberFormat('fr-MA', { style: 'currency', currency: 'MAD' })`) et dans les exports. Un module `shared/money.py` centralise conversions et formatage ; un `lib/money.ts` fait le miroir côté front.

Les frais d'inscription de 50 DH sont donc `5000`. Et ils sont stockés dans la table `parametre`, pas en dur : un centre qui passe à 60 DH ne doit pas nécessiter un déploiement.

### 6.2 Immuabilité des écritures financières

Aucun paiement, aucune ligne de paie validée n'est jamais modifié ni supprimé.

- **Correction d'un paiement** = annulation (`annule_le`, `annule_par`, `motif_annulation`) puis nouvelle saisie. La ligne d'origine reste visible, barrée, dans l'historique.
- **Paie validée** = verrouillée. Une régularisation se fait par une ligne d'ajustement sur le mois suivant.
- **Suppression d'un élève** = archivage (`statut = ARCHIVE`). Ses paiements passés doivent rester dans les comptes.

### 6.3 Figeage des tarifs

Le tarif est **copié**, pas référencé, au moment de l'engagement :

- `inscription_matiere.tarif_mensuel_cents` — figé à l'inscription de l'élève à la matière.
- `ligne_paie.tarif_unitaire_cents` — figé à la génération de la paie.

Modifier le tarif de référence n'affecte alors que les engagements futurs. C'est la garantie que les mois clôturés ne bougent plus jamais.

### 6.4 Idempotence

Tout endpoint d'écriture financière accepte un en-tête `Idempotency-Key`. La clé et la réponse sont stockées 24 h. Un double-clic ou un rejeu réseau renvoie la première réponse au lieu de créer un doublon de paiement. Sur une caisse manipulée par une secrétaire pressée, ce n'est pas un luxe.

### 6.5 Journal d'audit

Table `journal_audit` en **ajout seul** : `utilisateur_id`, `action`, `entite`, `entite_id`, `avant jsonb`, `apres jsonb`, `adresse_ip`, `horodatage`. Aucun `UPDATE` ni `DELETE` — à garantir par des privilèges Postgres restreints sur le rôle applicatif.

Sont journalisés : toute écriture sur les paiements, les tarifs, la paie, les charges, les utilisateurs et les statuts d'élève.

### 6.6 Permissions

Trois rôles, appliqués par une dépendance FastAPI (`Depends(exige_role(...))`) sur chaque route, jamais par du code conditionnel dans le corps du handler.

| Domaine | Administrateur | Caissier / Secrétaire | Professeur |
|---|---|---|---|
| Élèves | Complet | Créer, modifier | Lecture de ses niveaux |
| Paiements | Complet + annulation | Enregistrer | Aucun |
| Tarifs | Complet | Lecture | Aucun |
| Professeurs | Complet | Lecture | Sa fiche |
| Paie | Générer, valider | Aucun | Sa paie en lecture |
| Charges | Complet | Aucun | Aucun |
| Dashboard | Complet | Vue restreinte (sans bénéfice ni charges) | Aucun |
| Utilisateurs | Complet | Aucun | Aucun |
| Audit | Lecture | Aucun | Aucun |

Le point sensible : le caissier ne doit **pas** voir le bénéfice net ni les charges du centre. Ce sont deux endpoints distincts, pas un filtrage d'affichage côté client.

### 6.7 Fuseau horaire et périodes

Tout est stocké en UTC (`TIMESTAMPTZ`), affiché en `Africa/Casablanca`. Attention : le Maroc applique un décalage saisonnier lié au Ramadan — ne jamais coder un décalage fixe, laisser la base de données de fuseaux gérer.

Une période mensuelle est une colonne `periode CHAR(7)` au format `YYYY-MM`, avec une contrainte `CHECK`. C'est lisible, triable, indexable, et sans ambiguïté de fuseau.

---

## 7. Arborescence du projet

```
GEP/
├── CLAUDE.md
├── README.md
├── Makefile
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
│
├── docs/
│   ├── 00-cahier-des-charges.md
│   ├── 01-architecture.md          ← ce document
│   ├── 02-modele-donnees.md
│   ├── 03-decisions-ouvertes.md
│   ├── 04-roadmap.md
│   └── adr/                         décisions datées prises en cours de route
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                  création de l'app, montage des routeurs
│   │   ├── core/
│   │   │   ├── config.py            réglages via pydantic-settings
│   │   │   ├── security.py          JWT, hachage Argon2
│   │   │   ├── permissions.py       exige_role, exige_permission
│   │   │   ├── exceptions.py        exceptions métier + gestionnaires
│   │   │   ├── idempotence.py
│   │   │   └── logging.py           logs structurés JSON
│   │   ├── db/
│   │   │   ├── base.py              DeclarativeBase, mixins horodatage
│   │   │   ├── session.py           moteur async, dépendance get_session
│   │   │   └── seeds.py             niveaux, matières, catégories, admin initial
│   │   ├── shared/
│   │   │   ├── money.py             centimes ⇄ DH, formatage
│   │   │   ├── periode.py           manipulation YYYY-MM
│   │   │   ├── pagination.py
│   │   │   └── stockage.py          abstraction fichiers
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── referentiel/
│   │   │   ├── eleves/
│   │   │   ├── paiements/
│   │   │   ├── professeurs/
│   │   │   ├── paie/
│   │   │   ├── charges/
│   │   │   ├── dashboard/
│   │   │   ├── rapports/
│   │   │   │   ├── templates/       Jinja2 → PDF
│   │   │   │   ├── pdf.py
│   │   │   │   └── excel.py
│   │   │   └── audit/
│   │   └── taches/
│   │       ├── planificateur.py     APScheduler
│   │       ├── generer_echeances.py
│   │       └── generer_paie.py
│   └── tests/
│       ├── conftest.py
│       ├── factories/
│       ├── unit/                    services, calculs, sans base
│       ├── integration/             repositories, base réelle
│       └── e2e/                     endpoints via httpx
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── src/
│       ├── main.tsx
│       ├── api/
│       │   ├── client.ts            fetch + intercepteur refresh
│       │   └── generated/           ⚠ généré, ne pas éditer
│       ├── features/
│       │   ├── auth/
│       │   ├── eleves/
│       │   ├── paiements/
│       │   ├── professeurs/
│       │   ├── paie/
│       │   ├── charges/
│       │   ├── referentiel/
│       │   ├── dashboard/
│       │   └── rapports/
│       ├── components/
│       │   ├── ui/                  shadcn
│       │   └── layout/
│       ├── lib/
│       │   ├── money.ts
│       │   ├── dates.ts
│       │   └── permissions.ts
│       ├── routes/
│       └── stores/                  Zustand : session, préférences
│
└── infra/
    ├── nginx/nginx.conf
    └── scripts/
        ├── sauvegarde.sh            pg_dump quotidien
        └── restauration.sh
```

Chaque module de `features/` suit la même structure interne : `components/`, `hooks/`, `pages/`, `types.ts`.

---

## 8. Déploiement

Une seule machine. `docker-compose` avec trois services :

```
postgres  →  volume persistant
api       →  FastAPI derrière uvicorn
web       →  nginx, sert le build statique + proxy /api vers api
```

Les justificatifs sont dans un volume monté, inclus dans la sauvegarde.

**La sauvegarde n'est pas optionnelle.** `pg_dump` quotidien, conservation de 30 jours, copie hors machine. Et surtout : un test de restauration effectué au moins une fois avant la mise en production. Une sauvegarde jamais restaurée n'est pas une sauvegarde.

---

## 9. Stratégie de tests

L'effort de test se concentre là où une erreur coûte de l'argent, pas uniformément.

| Zone | Couverture visée | Type |
|---|---|---|
| Calcul de paie | **100 %** | Unitaire, cas limites inclus |
| Calcul des échéances et des impayés | **100 %** | Unitaire |
| Formule du bénéfice net | **100 %** | Unitaire |
| Paiements partiels et annulations | **100 %** | Intégration |
| Permissions par rôle | Tous les endpoints | E2E |
| CRUD référentiel | Correct | Intégration |
| Rendu des composants | Parcours principaux | Aucune obsession |

Les cas limites à couvrir explicitement dans les tests de paie : zéro élève sur une affectation, élève suspendu en milieu de mois, matière ajoutée le 20 du mois, tarif modifié après génération de la paie, paie déjà validée qu'on tente de régénérer, élève archivé avec des impayés.
