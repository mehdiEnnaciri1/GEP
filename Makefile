.PHONY: dev stop test lint migrate revision seed api-types sauvegarde

# Python du venv local du backend (créé par `python -m venv backend/.venv`), jamais
# celui du PATH : évite qu'une version ou un interpréteur global divergent de la
# version 3.12 documentée dans CLAUDE.md ne fausse silencieusement lint/tests.
BACKEND_PY := $(abspath $(or $(wildcard backend/.venv/Scripts/python.exe),backend/.venv/bin/python))

dev:
	docker compose up --build

stop:
	docker compose down

test:
	cd backend && PYTHONIOENCODING=utf-8 $(BACKEND_PY) -m pytest -v
	cd frontend && npm run test

lint:
	cd backend && PYTHONIOENCODING=utf-8 $(BACKEND_PY) -m ruff check . && PYTHONIOENCODING=utf-8 $(BACKEND_PY) -m mypy app
	cd frontend && npm run lint && npx tsc -b

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
