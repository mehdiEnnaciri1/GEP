# ADR — Mise à jour vers React 19 et React Router 7

**Contexte.** L'étape 0 avait épinglé React 18 et React Router v6, conformément
à la version documentée dans `CLAUDE.md` au moment du scaffolding. `react-router-dom`
6.30.4 (dernière version de la branche 6.x) reste concerné par un avis de
sécurité modéré (CVE-2025-68470 et une variante) : une redirection ouverte via
`<Link>`/`useNavigate` avec un antislash, corrigée uniquement à partir de la
7.18.x. La branche 6.x n'a pas reçu de correctif rétroporté. Par ailleurs,
l'écosystème (create-vite, shadcn/ui) installe React 19 par défaut depuis
plusieurs mois : rester sur 18 revient à s'écarter du chemin le mieux testé par
l'outillage, sans bénéfice pour une application qui ne dépend d'aucune API
React 18 spécifique.

**Décision.** Le frontend passe à `react`/`react-dom` 19.x et `react-router-dom`
7.x, en mode déclaratif (`BrowserRouter`/`Routes`/`Route`, comme en v6) — pas le
mode framework de React Router 7 (`@react-router/dev`), qui impose du SSR et un
second serveur de build : GEP reste un SPA statique servi par nginx, sans
changement à cette décision d'architecture (§2 de `docs/01-architecture.md`,
« Pas de Next.js »). Aucune API de routage utilisée dans le projet à ce stade
(étape 0, aucune route définie) n'est affectée par le passage de la v6 à la v7.

**Conséquences.** L'avis de sécurité sur `react-router-dom` disparaît
(`npm audit` : 0 vulnérabilité après migration). `@types/react` et
`@types/react-dom` passent en 19.x. shadcn/ui (déjà installé en mode Radix,
preset Nova) est compatible React 19 sans changement. Aucun code de
l'application n'a eu à changer : à ce stade, seule `App.tsx` existe, sans
routeur monté. Les futures étapes qui introduiront le routage (écrans par
module) utiliseront directement les API de React Router 7 en mode déclaratif.
