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

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev,pdf]"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
