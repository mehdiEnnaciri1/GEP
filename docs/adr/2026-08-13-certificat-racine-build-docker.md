# ADR — Face à un filtre TLS local : ajouter une autorité, jamais désactiver la vérification

**Contexte.** Le build de l'image `api` (`pip install -e ".[dev,pdf]"`) a
échoué avec `CERTIFICATE_VERIFY_FAILED : unable to get local issuer
certificate`. Reproduit avec l'image officielle nue
(`docker run --rm python:3.12-slim python -m pip download pip -d /tmp/x`),
donc indépendant du Dockerfile de GEP. Diagnostic confirmé par trois vérifications :
`apt-get update` (HTTP) fonctionne sans problème dans le conteneur — pas de
panne réseau plus large — ; l'horloge de la VM est correcte ; et surtout,
`openssl s_client` montre que le certificat présenté pour `pypi.org` est émis
par `CN=Avast Web/Mail Shield Root` — l'antivirus inspecte le trafic HTTPS
sortant en le re-signant avec son propre certificat. Ce certificat est
enregistré dans le magasin de confiance Windows (l'hôte reçoit un 200 sans
problème), mais un conteneur Linux embarque son propre magasin, minimal, qui
l'ignore : la poignée de main TLS échoue uniquement depuis l'intérieur des
conteneurs.

**L'exclusion côté hôte a été tentée et ne fonctionne pas.** Configurer
Avast pour exclure Docker Desktop / WSL2 de l'inspection HTTPS, puis
`wsl --shutdown` pour forcer la relecture de la règle, n'a rien changé : le
certificat vu depuis le conteneur reste signé par Avast après coup. Le trafic
de la VM WSL2 sort par une interface réseau virtuelle qu'Avast filtre
indépendamment des exclusions applicatives — l'exclusion ne couvre pas ce
chemin réseau sur ce poste.

**Décision.** Le remède retenu et implémenté est d'**ajouter** l'autorité de
certification d'Avast au magasin de confiance du conteneur, jamais de
désactiver la vérification TLS :

- Le certificat racine a été exporté (`infra/certs/avast-root.crt`, hors dépôt
  — voir `.gitignore`).
- `backend/Dockerfile` le copie dans l'image et appelle
  `update-ca-certificates`, puis configure `pip` pour utiliser ce magasin
  système (`pip config set global.cert`) avant tout `pip install`.
- Même traitement pour `frontend/Dockerfile` (`npm ci`) : Node n'utilise pas le
  magasin système, d'où `NODE_EXTRA_CA_CERTS` pointé sur le même certificat.
- Le contexte de build passe à la racine du dépôt (`context: .` dans
  `docker-compose.yml`) puisque le certificat vit dans `infra/certs/`, hors de
  `backend/` et `frontend/`.

Un dossier `infra/certs/` vide (juste un `.gitkeep` tracké) ne casse rien : le
`COPY` réussit, `update-ca-certificates` n'a simplement rien à ajouter. C'est
le cas sur toute machine où ce filtre TLS n'existe pas.

**Le principe reste le même** que pour le `pip` obsolète de l'hôte
(README) : un certificat ajouté au magasin de confiance reste une vérification
réelle contre une autorité explicitement approuvée. `--trusted-host` ou
`PIP_TRUSTED_HOST` suppriment la vérification purement et simplement — cette
option a été explicitement écartée, y compris comme solution temporaire.

**Conséquences.** Le certificat est spécifique à ce poste (et à cet
antivirus) : il n'est pas versionné, chaque développeur qui rencontre ce
symptôme exporte le sien (procédure dans `README.md`). Sur un poste sans ce
filtre TLS, le dossier reste vide et le build n'est pas affecté. Le même
principe s'appliquera en CI ou en production si l'environnement de build est
derrière un proxy d'entreprise équivalent (`docs/04-roadmap.md`, étape 10) :
le certificat de cet environnement-là devra être déposé dans `infra/certs/`
au moment du déploiement.
