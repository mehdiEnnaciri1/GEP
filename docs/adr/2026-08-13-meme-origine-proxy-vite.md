# ADR — Même origine front/API via proxy Vite, pas de CORS

**Contexte.** En développement, le front (`http://localhost:5173`) et l'API
(`http://localhost:8010`, remappée depuis le 8000 du conteneur — voir §4 de
cette liste de corrections) sont sur deux origines différentes. L'étape 1
(authentification) posera un refresh token dans un cookie `httpOnly`,
`SameSite=Strict` (choix déjà acté dans `docs/01-architecture.md` §2). Un
cookie `SameSite=Strict` n'est jamais envoyé sur une requête cross-site : si le
front appelle l'API sur une origine différente, le navigateur retient le
cookie et la requête échoue silencieusement — pas d'erreur explicite, juste un
utilisateur qui semble se déconnecter sans raison. Ajouter des en-têtes CORS
ne résout rien ici : CORS autorise une requête cross-origin, il ne change rien
au comportement de `SameSite=Strict` sur les cookies.

**Décision.** Le front n'appelle jamais l'API en URL absolue. Un proxy Vite
(`server.proxy['/api'] → http://localhost:8010`, `changeOrigin: true`) rend
l'API accessible sous `/api` depuis l'origine du front en développement.
Toutes les routes API sont donc préfixées par `/api` (`app.include_router(...,
prefix="/api")` dans `main.py`), à l'exception de `/health`, qui reste à la
racine — c'est cette route que le healthcheck Docker Compose du service `api`
interroge directement, sans passer par le front. En production, le service
`web` (nginx) reproduit exactement le même principe : il sert le build
statique et proxifie `/api` vers le service `api` (`docs/01-architecture.md`
§8) — le comportement dev et prod est donc identique, une seule origine dans
les deux cas, jamais deux à réconcilier avec des règles CORS.

**Conséquences.** Aucune configuration CORS à écrire ni à maintenir côté
FastAPI. Le cookie httpOnly de l'étape 1 fonctionnera dès le premier essai en
dev, sans débogage réseau surprise. Contrainte permanente pour tout le front :
un appel API s'écrit `fetch('/api/eleves')`, jamais
`fetch('http://localhost:8010/api/eleves')` — une URL absolue recrée
silencieusement le problème (voir la note dans `CLAUDE.md`, section Frontend).
Le port de l'API dans `vite.config.ts` (`8010`) devra rester synchronisé avec
celui de `docker-compose.yml` si l'un des deux change.
