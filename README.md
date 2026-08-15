# GEP — Gestion des Élèves et des Paiements

Application de gestion d'un centre de soutien scolaire marocain. Voir `CLAUDE.md`
et `docs/` pour le cahier des charges, l'architecture et la roadmap.

## Démarrage

Deux modes, selon ce que vous voulez vérifier :

**Développement courant** — postgres + api en conteneurs, front en natif (HMR) :

```bash
cp .env.example .env   # puis renseigner SECRET_KEY et les mots de passe
make dev                 # docker compose up : postgres + api uniquement
cd frontend && npm run dev
```

`/health` répond sur `http://localhost:8010/health`. Le front tourne sur
`http://localhost:5173` et atteint l'API via le proxy Vite `/api` (jamais
d'URL absolue ni de CORS — voir `docs/adr/2026-08-13-meme-origine-proxy-vite.md`).

**Vérification du build de production** — les trois services en conteneurs,
web servi par nginx comme en production :

```bash
docker compose --profile full up --build
```

Le port hôte de l'API est **8010** (le 8000 est déjà pris par un autre projet
sur ce poste — voir `docker-compose.yml`), remappé en interne vers le port 8000
du conteneur, sur lequel `uvicorn` écoute réellement.

## Si `make` n'est pas installé

Ce dépôt suppose GNU Make disponible (`choco install make`, `winget install
GnuWin32.Make`, ou tout simplement WSL/Git Bash avec make). S'il n'est pas
disponible sur votre poste, voici l'équivalent de chaque cible du `Makefile` :

| Cible | Commande équivalente |
|---|---|
| `make dev` | `docker compose up --build` (postgres + api ; `web` est exclu par défaut, voir `--profile full` ci-dessus) |
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
mise à jour ailleurs sur la machine (ex. `py -3.14`, si présente).

Ne contournez **jamais** la vérification TLS (`--trusted-host`) : passez plutôt
par une installation Python dont le `pip` est déjà à jour et fonctionne, pour
télécharger la roue de `pip` sans jamais désactiver la vérification :

```bash
py -3.14 -m pip download pip -d /tmp/pipwheel
cd backend
.venv/Scripts/python -m pip install --no-index --find-links /tmp/pipwheel --upgrade pip
```

(`py -3.14` peut être n'importe quelle autre installation Python déjà fonctionnelle
sur la machine — celle qui échoue est le `pip` fraîchement bootstrappé du venv,
pas Python 3.12 lui-même.) Une fois `pip` à jour, toutes les installations
suivantes (`-e ".[dev]"`, etc.) fonctionnent normalement, en ligne, sans aucun
contournement. Si ce n'est toujours pas le cas sur votre poste, le problème est
ailleurs (proxy d'entreprise, pare-feu) — dans ce cas, corrigez le magasin de
certificats de la machine plutôt que de désactiver la vérification TLS.

## Tests e2e du backend (`tests/e2e/`)

Ces tests ont besoin d'un vrai Postgres — jamais de mock pour ce qui touche à
la base. Deux modes, choisis par la variable d'environnement
`GEP_TEST_DATABASE_URL` :

**Base de test dédiée (recommandé en local, surtout si Docker Desktop est
instable sur ce poste)** — pas de conteneur à démarrer par test, juste une
connexion à une base déjà là :

```bash
docker compose exec postgres psql -U gep -c "CREATE DATABASE gep_test;"
export GEP_TEST_DATABASE_URL="postgresql+asyncpg://gep:<mot-de-passe-de-.env>@localhost:5432/gep_test"
cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/e2e -v
```

**`gep_test` doit être une base distincte de la base de dev** (`gep`) : les
tests vident toutes les tables après chaque test (`TRUNCATE ... CASCADE`) —
pointer `GEP_TEST_DATABASE_URL` sur la base de dev effacerait vos données de
développement à la première exécution.

**Si la commande ci-dessus échoue avec `ConnectionDoesNotExistError` /
`ConnectionResetError` (WinError 64)** : c'est le chemin réseau hôte → conteneur
qui est instable sur ce poste (Docker Desktop/WSL2), pas un problème de code —
déjà rencontré plusieurs fois pendant le développement. Le contournement fiable
est de lancer pytest **depuis l'intérieur du conteneur `api`**, qui parle à
postgres par le réseau Docker interne (`postgres:5432`, jamais `localhost`) :

```bash
docker compose exec -e GEP_TEST_DATABASE_URL="postgresql+asyncpg://gep:<mot-de-passe-de-.env>@postgres:5432/gep_test" api python -m pytest tests/e2e -v
```

**testcontainers (par défaut, sans la variable)** — un Postgres jetable démarré
et détruit pour la session de tests, le bon choix en CI où Docker est fiable et
où il n'y a pas de base de dev à préserver :

```bash
cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/e2e -v
```

Dans les deux cas, les migrations Alembic sont jouées une fois au début de la
session de tests, sur la base ciblée.

## Build Docker derrière un filtre TLS local

**Symptôme.** `docker compose up --build` échoue à l'étape `pip install` de
l'image `api` avec :

```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate ...'))
```

Reproductible indépendamment du Dockerfile de GEP, avec l'image officielle nue :

```bash
docker run --rm python:3.12-slim python -m pip download pip -d /tmp/x
```

**Cause.** Un antivirus ou un proxy d'entreprise qui inspecte le trafic HTTPS
(Avast, Kaspersky, ESET, proxy MITM d'entreprise...) re-signe les connexions
TLS sortantes avec son propre certificat racine. Ce certificat est installé
dans le magasin de confiance Windows — c'est pour ça que `pip` fonctionne sur
l'hôte — mais un conteneur Linux a son propre magasin, minimal, qui ne le
connaît pas. La poignée de main TLS échoue donc uniquement depuis l'intérieur
des conteneurs, jamais depuis l'hôte. Diagnostic à confirmer avant de toucher
à quoi que ce soit :

```bash
docker run --rm python:3.12-slim bash -lc "apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq openssl >/dev/null 2>&1 && echo | openssl s_client -connect pypi.org:443 -servername pypi.org 2>/dev/null | openssl x509 -noout -issuer -subject -dates"
```

Si `issuer` mentionne un antivirus ou une organisation qui n'est pas une
autorité publique connue, c'est confirmé.

**Sur ce projet, l'exclusion côté hôte a été tentée et ne suffit pas.**
Configurer Avast pour exclure Docker Desktop / WSL2 de l'inspection HTTPS, puis
`wsl --shutdown`, n'a rien changé : le trafic de la VM WSL2 sort par une
interface réseau virtuelle qu'Avast filtre indépendamment de cette exclusion.
Le remède retenu est donc l'injection du certificat racine dans l'image —
voir `docs/adr/2026-08-13-certificat-racine-build-docker.md`.

**Exporter le certificat racine depuis le magasin Windows**, en PEM (le format
qu'attend `update-ca-certificates`) :

```powershell
$cert = Get-ChildItem Cert:\LocalMachine\Root, Cert:\CurrentUser\Root |
    Where-Object Subject -like "*Avast*" | Select-Object -First 1
$b64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
"-----BEGIN CERTIFICATE-----`n$b64`n-----END CERTIFICATE-----" |
    Set-Content -Encoding ascii infra\certs\avast-root.crt
```

Adapter le filtre `-like "*Avast*"` au nom de l'antivirus ou du proxy concerné.
Le fichier va dans `infra/certs/` (non versionné, propre à chaque poste — voir
`.gitignore`). Un `infra/certs/.gitkeep` est tracké pour que le dossier existe
toujours : `backend/Dockerfile` et `frontend/Dockerfile` y copient son contenu
avant tout `pip install` / `npm ci`, que le dossier soit vide (rien à ajouter,
comportement normal sur un poste sans filtre TLS) ou qu'il contienne un
certificat.

**Ce qu'on ne fait jamais** : `--trusted-host`, `PIP_TRUSTED_HOST`,
`NODE_TLS_REJECT_UNAUTHORIZED=0`, ou toute autre façon de désactiver la
vérification TLS dans une image. Un certificat racine ajouté au magasin de
confiance du conteneur est une extension légitime de la confiance ; désactiver
la vérification revient à ne plus vérifier du tout qui se trouve à l'autre
bout de la connexion — y compris en production.
