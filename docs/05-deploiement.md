# GEP — Déploiement

Procédure pour un VPS Linux neuf, avec Docker et docker-compose. Aucun
hébergeur particulier n'est ciblé — ces instructions supposent seulement un
accès SSH root (ou sudo) à une machine Debian/Ubuntu récente, avec un nom de
domaine qui pointe déjà dessus.

Trois services en production (voir `docs/01-architecture.md` §8) :

```
postgres  →  volume persistant, aucun port exposé
api       →  FastAPI derrière uvicorn, aucun port exposé
nginx     →  sert le build statique + proxy /api vers api, HTTPS, 80 et 443
```

---

## 1. Préparation de la machine

```bash
# Système à jour
apt update && apt upgrade -y

# Docker (méthode officielle)
curl -fsSL https://get.docker.com | sh

# docker-compose est inclus dans Docker récent via `docker compose` (sans
# tiret) — vérifier :
docker compose version

# Pare-feu minimal : SSH, HTTP, HTTPS
apt install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Un utilisateur dédié, pas root, pour faire tourner le déploiement
adduser gep-deploy
usermod -aG docker gep-deploy
```

À partir d'ici, toutes les commandes s'exécutent en tant que `gep-deploy`,
depuis le répertoire où le dépôt est cloné (ex. `/home/gep-deploy/gep`).

```bash
su - gep-deploy
git clone <url-du-depot> gep
cd gep
```

## 2. DNS

Créer un enregistrement `A` (et `AAAA` si IPv6) pointant le nom de domaine
choisi vers l'IP publique du serveur. Attendre la propagation avant de passer
à l'étape suivante — `dig +short mon-domaine.ma` doit renvoyer l'IP du
serveur depuis une machine externe.

## 3. Variables d'environnement de production

Aucun `.env` n'est committé pour la production (voir `docker-compose.prod.yml`).
Créer `.env.prod` **sur le serveur uniquement**, jamais dans le dépôt :

```bash
cat > .env.prod <<'EOF'
POSTGRES_USER=gep
POSTGRES_PASSWORD=<mot-de-passe-long-et-aleatoire>
POSTGRES_DB=gep
SECRET_KEY=<cle-aleatoire-64-caracteres-minimum>
DOMAIN_NAME=gep.mon-domaine.ma
EOF
chmod 600 .env.prod
```

Générer des valeurs aléatoires plutôt que les inventer :

```bash
openssl rand -hex 32   # pour SECRET_KEY
openssl rand -hex 24   # pour POSTGRES_PASSWORD
```

`SAUVEGARDE_GPG_PASSPHRASE` (passphrase de chiffrement des sauvegardes) se
génère et se stocke à part — voir `docs/06-exploitation.md` §Sauvegarde,
**jamais dans `.env.prod`** : si ce fichier est un jour compromis, la
passphrase des sauvegardes ne doit pas l'être avec.

## 4. Premier certificat Let's Encrypt

Le certificat doit exister **avant** le premier démarrage de nginx (qui le
lit dès son démarrage). Bootstrap en deux temps : nginx démarre d'abord en
HTTP seul le temps d'obtenir le certificat, puis on bascule la configuration
complète.

```bash
mkdir -p infra/certbot/www infra/certbot/conf

# 1. Démarrer temporairement nginx en HTTP seul pour servir le challenge ACME.
#    (Le gabarit infra/nginx/app.conf.template sert déjà /.well-known/acme-challenge/
#    sur le port 80 avant toute redirection HTTPS — le certificat n'existe pas
#    encore à ce stade, donc le bloc 443 échouerait à démarrer : commenter
#    temporairement le bloc `server { listen 443 ... }` si nginx refuse de
#    démarrer sans certificat, ou utiliser `certbot certonly --standalone`
#    à la place si le service nginx n'a pas encore démarré du tout.)

docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm \
    --entrypoint "certbot certonly --webroot -w /var/www/certbot \
        -d gep.mon-domaine.ma --email vous@mon-domaine.ma --agree-tos --no-eff-email" \
    certbot

# 2. Démarrer la pile complète — nginx trouve maintenant le certificat.
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Si `certbot certonly --webroot` échoue parce que rien ne sert encore le
challenge sur le port 80, démarrer d'abord uniquement nginx et postgres/api :

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres api nginx
```

nginx sert déjà `/.well-known/acme-challenge/` sur le port 80 même sans
certificat valide pour le bloc 443 tant que ce dernier n'est pas sollicité —
en pratique la plupart des images nginx récentes démarrent malgré un bloc
443 en échec de lecture de certificat ; si ce n'est pas le cas ici, relancer
la commande `certbot certonly` avec `--standalone` sur le port 80 avant que
nginx ne démarre.

## 5. Migrations et données de référence

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm \
    api alembic upgrade head

docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm \
    -e ADMIN_INITIAL_EMAIL=admin@mon-domaine.ma \
    -e ADMIN_INITIAL_PASSWORD=<mot-de-passe-temporaire-a-changer> \
    api python -m app.db.seeds
```

`ADMIN_INITIAL_EMAIL`/`ADMIN_INITIAL_PASSWORD` sont passés uniquement pour
cette commande ponctuelle (`run`, pas `up`) — ils ne restent pas dans
l'environnement du conteneur `api` qui tourne en continu.

## 6. Vérification

```bash
curl -I https://gep.mon-domaine.ma/health
```

Doit renvoyer `HTTP/2 200`. Vérifier aussi dans un navigateur que l'écran de
connexion s'affiche et que la connexion avec le compte admin créé à l'étape 5
fonctionne.

## 7. Sauvegardes automatiques (cron)

```bash
crontab -e
```

Ajouter :

```cron
0 3 * * * cd /home/gep-deploy/gep && \
  POSTGRES_USER=gep POSTGRES_DB=gep \
  SAUVEGARDE_GPG_PASSPHRASE=<passphrase-des-sauvegardes> \
  SAUVEGARDE_RSYNC_DEST=<utilisateur@serveur-distant:/chemin> \
  ./infra/scripts/sauvegarde.sh >> /var/log/gep-sauvegarde.log 2>&1

# Renouvellement du certificat, deux fois par mois — certbot ne renouvelle
# que s'il reste moins de 30 jours de validité, l'appel répété ne coûte rien.
0 4 1,15 * * cd /home/gep-deploy/gep && \
  docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot renew && \
  docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload
```

Ne JAMAIS committer la passphrase ou la destination rsync dans le dépôt —
elles vivent uniquement dans la crontab de ce serveur (ou un fichier
d'environnement séparé, chargé par la crontab, lui aussi hors dépôt).

**Avant de considérer le déploiement terminé : faire un test de
restauration** (voir `docs/06-exploitation.md` §Test de restauration) — une
sauvegarde jamais restaurée n'est pas une sauvegarde.

---

## Mise à jour

```bash
cd /home/gep-deploy/gep
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

`docker compose up -d` ne recrée que les conteneurs dont l'image ou la
configuration a changé — un service inchangé n'est pas redémarré.

**Toujours faire une sauvegarde manuelle avant une mise à jour qui touche au
schéma de la base** (une nouvelle migration) :

```bash
POSTGRES_USER=gep POSTGRES_DB=gep SAUVEGARDE_GPG_PASSPHRASE=<passphrase> \
    ./infra/scripts/sauvegarde.sh
```

## Rollback

Si une mise à jour pose problème :

```bash
cd /home/gep-deploy/gep
git log --oneline -5          # identifier le commit précédent stable
git checkout <commit-precedent>
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

**Si la mise à jour problématique incluait une migration Alembic qui a déjà
tourné**, revenir au code précédent ne suffit pas : la base a un schéma plus
récent que le code restauré. Deux options, du plus sûr au plus rapide :

1. Restaurer la sauvegarde faite juste avant la mise à jour (voir
   `docs/06-exploitation.md` §Restauration) — perd les écritures faites
   depuis, mais garantit la cohérence schéma/code.
2. `alembic downgrade -1` (ou jusqu'à la révision correspondant au commit
   restauré) avant de redémarrer l'API — seulement si toutes les migrations
   concernées ont un `downgrade()` correct (c'est une exigence du projet,
   voir CLAUDE.md) et qu'aucune donnée créée entre-temps ne dépend des
   colonnes/tables supprimées par ce downgrade.

Dans le doute, l'option 1 est toujours la plus sûre — c'est précisément pour
ce genre de situation que le test de restauration n'est pas optionnel.
