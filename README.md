# GEP — Gestion des Élèves et des Paiements

Application de gestion d'un centre de soutien scolaire marocain. Voir `CLAUDE.md`
et `docs/` pour le cahier des charges, l'architecture et la roadmap.

## Démarrage

```bash
cp .env.example .env   # puis renseigner SECRET_KEY et les mots de passe
make dev                # postgres + api + web, via docker compose
```

`/health` doit répondre sur `http://localhost:8000/health`, le front sur
`http://localhost:5173`.

## Si `make` n'est pas installé

Ce dépôt suppose GNU Make disponible (`choco install make`, `winget install
GnuWin32.Make`, ou tout simplement WSL/Git Bash avec make). S'il n'est pas
disponible sur votre poste, voici l'équivalent de chaque cible du `Makefile` :

| Cible | Commande équivalente |
|---|---|
| `make dev` | `docker compose up --build` |
| `make stop` | `docker compose down` |
| `make test` | `cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest -v` puis `cd frontend && npm run test` |
| `make lint` | `cd backend && .venv/Scripts/python -m ruff check . && .venv/Scripts/python -m mypy app` puis `cd frontend && npm run lint && npx tsc -b` |
| `make migrate` | `cd backend && alembic upgrade head` |
| `make revision m="message"` | `cd backend && alembic revision --autogenerate -m "message"` |
| `make seed` | `cd backend && python -m app.db.seeds` |
| `make api-types` | `curl -s http://localhost:8000/openapi.json > /tmp/openapi.json` puis `cd frontend && npx openapi-typescript /tmp/openapi.json -o src/api/generated/schema.d.ts` |
| `make sauvegarde` | `./infra/scripts/sauvegarde.sh` |

Sur Linux/macOS, remplacer `.venv/Scripts/python` par `.venv/bin/python`.

## Environnement local du backend (hors Docker)

```bash
cd backend
python -m venv .venv          # Python 3.12, pas une autre version — voir CLAUDE.md
.venv/Scripts/python -m pip install -e ".[dev]"     # ajouter ",pdf" pour tester les exports PDF
```

**Piège connu (Windows).** Le `pip` installé automatiquement par `ensurepip` dans
un venv fraîchement créé peut être une version ancienne (ex. 24.0) dont le
magasin de certificats vendorisé ne valide plus la chaîne TLS actuelle de
pypi.org (`CERTIFICATE_VERIFY_FAILED`). Le symptôme n'apparaît que sur ce
premier `pip install` — pas sur une installation Python plus récente ou déjà
mise à jour ailleurs sur la machine. La correction est de mettre à jour `pip`
lui-même, en contournant une seule fois la vérification TLS pour cette étape
précise (c'est un problème d'œuf et de poule : l'ancien pip ne peut pas se
mettre à jour tout seul via une connexion qu'il ne valide pas) :

```bash
.venv/Scripts/python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip
```

Une fois `pip` à jour, toutes les installations suivantes (`-e ".[dev]"`, etc.)
fonctionnent normalement, sans `--trusted-host`. Si ce n'est pas le cas sur
votre poste, le problème est ailleurs (proxy d'entreprise, pare-feu) : ne pas
généraliser le contournement à l'ensemble des commandes `pip`.
