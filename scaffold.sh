#!/usr/bin/env bash
# GEP — création de l'arborescence du projet
#
# Usage :
#   1. Placer ce script dans le dossier GEP/ (à côté de CLAUDE.md et docs/)
#   2. chmod +x scaffold.sh && ./scaffold.sh
#
# Le script est idempotent : il ne détruit rien, il crée ce qui manque.

set -euo pipefail

echo "→ Création de l'arborescence GEP"

# ---------------------------------------------------------------- backend
mkdir -p backend/alembic/versions
mkdir -p backend/app/{core,db,shared,taches}
mkdir -p backend/tests/{unit,integration,e2e,factories}

MODULES=(auth referentiel eleves paiements professeurs paie charges dashboard rapports audit)
for m in "${MODULES[@]}"; do
    mkdir -p "backend/app/modules/$m"
    touch "backend/app/modules/$m/__init__.py"
    # Les quatre couches, systématiquement
    for f in models schemas repository service router; do
        [ -f "backend/app/modules/$m/$f.py" ] || echo "\"\"\"$m — $f\"\"\"" > "backend/app/modules/$m/$f.py"
    done
done

mkdir -p backend/app/modules/rapports/templates
mkdir -p backend/app/modules/rapports/static/fonts   # Noto Sans Arabic ici

# __init__.py des packages
for d in backend/app backend/app/core backend/app/db backend/app/shared \
         backend/app/taches backend/app/modules backend/tests; do
    touch "$d/__init__.py"
done

# ---------------------------------------------------------------- frontend
mkdir -p frontend/src/{api/generated,components/{ui,layout},lib,routes,stores,styles}

FEATURES=(auth referentiel eleves paiements professeurs paie charges dashboard rapports)
for f in "${FEATURES[@]}"; do
    mkdir -p "frontend/src/features/$f"/{components,hooks,pages}
    touch "frontend/src/features/$f/types.ts"
done

mkdir -p frontend/public

cat > frontend/src/api/generated/.gitkeep <<'EOF'
Contenu généré par `make api-types`. Ne pas éditer à la main.
EOF

# ---------------------------------------------------------------- infra & docs
mkdir -p infra/nginx infra/scripts
mkdir -p docs/adr
mkdir -p donnees/justificatifs        # volume monté, ignoré par git

# ---------------------------------------------------------------- fichiers racine
if [ ! -f .gitignore ]; then
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Node
node_modules/
dist/
.vite/

# Environnement
.env
.env.local
*.local

# Données — jamais dans git
donnees/
sauvegardes/
*.dump
*.sql.gz

# Éditeurs
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
.idea/
.DS_Store
EOF
fi

if [ ! -f .env.example ]; then
cat > .env.example <<'EOF'
# ---- Base de données
POSTGRES_USER=gep
POSTGRES_PASSWORD=changez_moi
POSTGRES_DB=gep
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# ---- Application
APP_ENV=development
SECRET_KEY=changez_moi_en_production_64_caracteres_aleatoires
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_JOURS=7
FUSEAU_HORAIRE=Africa/Casablanca
DEVISE=MAD

# ---- Fichiers
CHEMIN_JUSTIFICATIFS=/donnees/justificatifs
TAILLE_MAX_FICHIER_MO=5

# ---- Frontend
VITE_API_URL=http://localhost:8000
EOF
fi

if [ ! -f Makefile ]; then
cat > Makefile <<'EOF'
.PHONY: dev stop test lint migrate revision seed api-types sauvegarde

dev:
	docker compose up --build

stop:
	docker compose down

test:
	cd backend && pytest -v
	cd frontend && npm run test

lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint && npx tsc --noEmit

migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

seed:
	cd backend && python -m app.db.seeds

api-types:
	curl -s http://localhost:8000/openapi.json > /tmp/openapi.json
	cd frontend && npx openapi-typescript /tmp/openapi.json -o src/api/generated/schema.d.ts

sauvegarde:
	./infra/scripts/sauvegarde.sh
EOF
fi

echo
echo "✓ Arborescence créée."
echo
echo "Prochaines étapes :"
echo "  1. cp .env.example .env  puis renseigner SECRET_KEY et les mots de passe"
echo "  2. git init && git add . && git commit -m 'socle projet'"
echo "  3. Ouvrir le dossier dans VS Code, lancer Claude Code"
echo "  4. Première consigne : « Lis CLAUDE.md et docs/, puis réalise l'étape 0"
echo "     de docs/04-roadmap.md »"
