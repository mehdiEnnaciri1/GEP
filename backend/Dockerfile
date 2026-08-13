FROM python:3.12-slim

WORKDIR /app

# Dépendances système pour argon2-cffi et pour WeasyPrint (rendu PDF, §9 roadmap,
# extra [pdf] — voir docs/adr/*-weasyprint-extra-optionnel.md). Noms de paquets
# vérifiés pour Debian bookworm (base de python:3.12-slim) : libgdk-pixbuf2.0-0 y
# est un paquet de transition, on dépend directement de libgdk-pixbuf-2.0-0.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 libharfbuzz0b libfribidi0 \
    fonts-dejavu-core fonts-noto-core \
    libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Autorité(s) de certification locale(s) — nécessaire uniquement sur les postes
# ou réseaux où un antivirus ou un proxy d'entreprise inspecte le trafic HTTPS
# (voir docs/adr/2026-08-13-certificat-racine-build-docker.md). infra/certs/
# est vide sur une machine sans ce filtre : update-ca-certificates n'ajoute
# alors rien, et pip continue de vérifier TLS normalement contre les autorités
# publiques habituelles. On déclare une autorité de confiance de plus, on ne
# désactive jamais la vérification.
COPY infra/certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates && \
    pip config set global.cert /etc/ssl/certs/ca-certificates.crt

COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev,pdf]"

COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
