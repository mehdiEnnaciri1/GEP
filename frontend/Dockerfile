FROM node:22-slim

WORKDIR /app

# Voir backend/Dockerfile et docs/adr/2026-08-13-certificat-racine-build-docker.md :
# même filtre TLS local possible. Node n'utilise pas le magasin système, d'où
# NODE_EXTRA_CA_CERTS plutôt que update-ca-certificates. Ce service est derrière
# le profil "full" (non buildé par défaut), mais autant ne pas laisser une
# bombe à retardement pour qui l'active sur un poste filtré.
COPY infra/certs/ /usr/local/share/ca-certificates/
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/avast-root.crt

COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci

COPY frontend/ .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
