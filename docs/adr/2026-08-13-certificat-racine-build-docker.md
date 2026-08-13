# ADR — Face à un filtre TLS local : ajouter une autorité, jamais désactiver la vérification

**Contexte.** Le build de l'image `api` (`pip install -e ".[dev,pdf]"`) a
échoué avec `CERTIFICATE_VERIFY_FAILED : unable to get local issuer
certificate`. Reproduit avec l'image officielle nue
(`docker run --rm python:3.12-slim python -m pip download pip -d /tmp/x`),
donc indépendant du Dockerfile de GEP. Diagnostic : la variable d'environnement
système `SSLKEYLOGFILE=\\.\aswMonFltProxy\...` trahit le pilote réseau
d'Avast — l'antivirus inspecte le trafic HTTPS sortant en le re-signant avec
son propre certificat racine. Ce certificat est enregistré dans le magasin de
confiance Windows (l'hôte valide donc la connexion sans problème), mais un
conteneur Linux embarque son propre magasin, minimal, qui l'ignore. La
poignée de main TLS échoue uniquement depuis l'intérieur des conteneurs.

**Décision.** Le remède est d'**ajouter** l'autorité de certification qui
intercepte le trafic au magasin de confiance du conteneur
(`update-ca-certificates`, après avoir copié le certificat dans l'image), pas
de désactiver la vérification TLS. Concrètement, à distinguer :

- **Root cause locale, remède immédiat** : exclure Docker Desktop / WSL2 de
  l'inspection HTTPS côté antivirus. C'est ce qui a débloqué ce poste-ci —
  rien à changer dans le projet, aucune trace dans le Dockerfile.
- **Remède portable, pas encore implémenté** : si ce projet est buildé sur un
  autre poste, une CI, ou un serveur derrière un proxy d'entreprise qui fait
  la même inspection, la même erreur réapparaîtra. Le Dockerfile devra alors
  copier le certificat racine concerné dans l'image et appeler
  `update-ca-certificates` avant tout `pip install` — non fait ici : ça
  élargirait le contexte de build à la racine du dépôt (le certificat n'a pas
  sa place dans `backend/`) et n'est pas justifié tant que l'exclusion côté
  hôte suffit. Point ouvert noté dans `docs/04-roadmap.md`, étape 10
  (déploiement).

C'est la même distinction que dans `README.md` pour le `pip` de l'hôte
(bootstrap obsolète, corrigé en mettant `pip` à jour, jamais en désactivant la
vérification) : un certificat ajouté au magasin de confiance reste une
vérification réelle contre une autorité explicitement approuvée ; `--trusted-host`
ou `PIP_TRUSTED_HOST` suppriment la vérification purement et simplement — y
compris en production, si l'habitude s'installait.

**Conséquences.** Aucun changement dans `backend/Dockerfile` pour l'instant.
Le jour où ce symptôme réapparaît (autre poste, CI, serveur de déploiement), le
diagnostic est déjà écrit : vérifier d'abord si un antivirus/proxy local est en
cause (variable d'environnement du type `SSLKEYLOGFILE`, ou test direct avec
l'image officielle nue), avant de toucher au Dockerfile. Si l'exclusion côté
hôte n'est pas possible sur cet environnement-là (poste d'un autre développeur
sans droits admin, CI managée, serveur de prod derrière un proxy d'entreprise
permanent), l'injection du certificat devient nécessaire et devra être en place
avant le déploiement de l'étape 10.
