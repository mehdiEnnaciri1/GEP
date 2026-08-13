# GEP — Instructions projet

Application web de gestion d'un centre de soutien scolaire marocain : élèves,
paiements, paie des professeurs, charges du centre.

Documents de référence, à lire avant toute tâche non triviale :
- `docs/00-cahier-des-charges.md` — le besoin exprimé par le client
- `docs/01-architecture.md` — stack, couches, arborescence
- `docs/02-modele-donnees.md` — schéma et règles de calcul
- `docs/03-decisions-ouvertes.md` — arbitrages et leurs justifications
- `docs/04-roadmap.md` — ordre de construction

---

## Stack

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16,
Pydantic v2, pytest.
**Frontend** — React 19, TypeScript, Vite, React Router 7, TanStack Query, TanStack Table,
React Hook Form + Zod, Tailwind, shadcn/ui, Recharts. Voir `docs/adr/2026-08-13-react-19-react-router-7.md`
pour la justification de la mise à jour depuis React 18 / React Router 6.

---

## Règles inviolables

### Argent

**Tous les montants sont des entiers en centimes** (`BIGINT` en base, `int` en Python,
`number` en TS). Jamais de `float`, jamais de `Decimal` en base, jamais de division
flottante.

La conversion en dirhams a lieu uniquement à l'affichage et dans les exports, via
`shared/money.py` et `lib/money.ts`. Aucun autre fichier ne formate un montant.

Si tu écris `montant / 100` ailleurs que dans ces deux modules, c'est une erreur.

### Écritures financières

- Un `paiement` n'est jamais modifié ni supprimé. Correction = annulation (`annule_le`,
  `annule_par`, `motif_annulation`) puis nouvelle saisie.
- Une `paie_mensuelle` en statut `VALIDEE` ou `PAYEE` est verrouillée. Correction =
  ligne d'ajustement sur la période suivante.
- Un élève n'est jamais supprimé : `statut = ARCHIVE`.
- Toute écriture financière est journalisée dans `journal_audit`, dans la même
  transaction.

### Tarifs

Les tarifs sont **copiés** au moment de l'engagement, pas référencés :
`inscription_matiere.tarif_mensuel_cents` et `ligne_paie.tarif_unitaire_cents`.

Ne jamais recalculer un montant passé à partir du référentiel de tarifs actuel.

### Couches

```
router.py       → HTTP uniquement
service.py      → métier, frontière transactionnelle
repository.py   → requêtes SQLAlchemy
```

- Aucun `HTTPException` dans un service. Lève une exception métier de
  `core/exceptions.py`, un gestionnaire global la traduit.
- Aucune requête SQLAlchemy dans un router ni dans un service : passe par le repository.
- Aucune règle métier dans un repository.
- Aucun modèle ORM retourné par un endpoint : toujours un schéma Pydantic de sortie.

### Base de données

- Tout changement de schéma passe par une migration Alembic. Jamais de `create_all()`
  en dehors des tests.
- Les migrations sont réversibles (`downgrade` rempli).
- Les contraintes métier exprimables en SQL (`CHECK`, `UNIQUE`, `FOREIGN KEY`) sont dans
  la base, pas seulement dans le code applicatif.

### Permissions

Toute route porte une dépendance explicite : `Depends(exige_role(Role.ADMIN))`.
Jamais de vérification de rôle dans le corps du handler, jamais de route sans
dépendance d'autorisation — même en lecture.

Le rôle `CAISSIER` ne doit accéder ni aux charges, ni au bénéfice net, ni à la paie.
Ce sont des endpoints séparés, pas un filtrage côté client.

### Frontend

- `src/api/generated/` est **généré** par `make api-types`. Ne jamais l'éditer à la main.
- Pas de `fetch` direct dans un composant : toujours un hook TanStack Query dans
  `features/<module>/hooks/`.
- Pas de `<form>` HTML natif avec soumission par défaut : React Hook Form et
  gestionnaires `onClick` / `onSubmit` contrôlés.
- Les schémas Zod reflètent les schémas Pydantic. Si l'un change, l'autre change.

---

## Conventions

**Nommage** — le domaine est en français : `eleve`, `paiement`, `professeur`,
`echeance`, `charge`. Le code technique est en anglais (`get`, `list`, `create`,
`Repository`, `Service`). Ne pas mélanger dans un même identifiant : `get_eleve_by_id`,
pas `obtenir_eleve_par_id` ni `get_student_by_id`.

**Tables** — au singulier : `eleve`, pas `eleves`.

**Modules** — `backend/app/modules/<nom>/` et `frontend/src/features/<nom>/` portent
le même nom.

**Périodes** — chaîne `YYYY-MM`. Les helpers sont dans `shared/periode.py`.

**Dates** — `TIMESTAMPTZ` en UTC en base, affichage en `Africa/Casablanca`. Ne jamais
coder un décalage horaire en dur : le Maroc change d'heure de façon non standard.

---

## Tests

Obligatoires, sans exception, pour :
- tout calcul de montant (paie, échéance, impayés, bénéfice net) — viser 100 %
- tout endpoint d'écriture
- toute permission par rôle

Le calcul de paie et le calcul d'échéance ont des tests unitaires couvrant au minimum :
zéro élève sur une affectation, élève suspendu en milieu de mois, matière ajoutée en
cours de mois, tarif modifié après génération, paie déjà validée, élève archivé avec
impayés.

Un test qui appelle la vraie base va dans `tests/integration/`, pas dans `tests/unit/`.

---

## Commandes

```bash
make dev          # docker-compose up : postgres + api + web
make migrate      # alembic upgrade head
make revision m="ajout table charge"
make test         # pytest + vitest
make lint         # ruff + mypy + eslint + tsc
make api-types    # régénère frontend/src/api/generated/
make seed         # niveaux, matières, catégories, admin initial
```

---

## Méthode de travail attendue

**Une tranche verticale à la fois.** Un module complet — modèle, migration, repository,
service, tests de service, router, tests d'endpoint, puis écran front — avant de passer
au suivant. Ne pas créer toutes les tables d'un coup : le schéma s'affine au contact de
l'implémentation.

**Avant d'écrire du code sur un module, relis** `docs/02-modele-donnees.md` pour la
partie concernée. Les règles de calcul y sont écrites en toutes lettres ; ne les
réinvente pas.

**Si une exigence du cahier des charges est ambiguë**, ne devine pas : vérifie d'abord
si elle figure dans `docs/03-decisions-ouvertes.md`. Si oui, applique la décision
retenue. Sinon, signale l'ambiguïté et propose une option par défaut plutôt que de
choisir en silence.

**Une décision d'architecture prise en cours de route** se documente dans un fichier
daté sous `docs/adr/`. Trois paragraphes suffisent : le contexte, la décision, les
conséquences.
