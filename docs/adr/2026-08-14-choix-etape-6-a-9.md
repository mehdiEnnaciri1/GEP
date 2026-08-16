# ADR — Trois choix des étapes 6 à 9 : période du dashboard, PDF paresseux, détection MIME manuelle

## 1. Le dashboard affiche des périodes calendaires (`YYYY-MM`), pas des « mois d'année scolaire »

**Contexte.** L'année scolaire marocaine commence en septembre, pas en janvier. Un
utilisateur qui raisonne en « mois 1, mois 2… » de l'année scolaire (septembre =
mois 1, octobre = mois 2, etc.) doit mentalement décaler de huit mois pour
retrouver le `YYYY-MM` calendaire que la période du dashboard attend. Ce
décalage est une source réelle de confusion à l'usage (« le mois 2 c'est
octobre ou février ? »), et le cahier des charges ne tranche pas la question.

**Décision.** Le dashboard garde une période calendaire brute (`CHAR(7)`,
`YYYY-MM`), exactement comme `echeance.periode`, `charge.periode` et
`paie_mensuelle.periode` — aucune réindexation « mois 1 à 10 de l'année
scolaire » n'est introduite, ni en base, ni dans les requêtes du repository.
La raison : le dashboard agrège des données produites par trois autres
modules (paiements, charges, paie), tous période-calendaire ; lui seul
parlant en « mois scolaire » obligerait à traduire dans un sens à l'écriture
des filtres de requête et dans l'autre à l'affichage, pour un unique écran,
sans que la donnée sous-jacente change de nature.

**Conséquences.** L'API et le modèle restent uniformes sur tout le projet :
un seul concept de période, une seule contrainte `CHECK`, un seul format à
valider partout. Le confort d'un libellé « Mois 2 de l'année scolaire
2025-2026 » reste possible plus tard, mais **uniquement comme calcul
d'affichage côté front** (à partir de la date de début de l'année scolaire
active), jamais comme clé de stockage ou de filtre — à faire quand un besoin
réel se présente, pas maintenant.

## 2. WeasyPrint reste importé en paresseux dans la fonction — l'ADR précédent est confirmé, pas remplacé

**Contexte.** L'ADR `2026-08-13-weasyprint-extra-optionnel.md` imposait déjà
un import paresseux de `weasyprint`, à l'intérieur de la fonction qui génère
le PDF, jamais au niveau du module — pour qu'importer `app.modules.rapports`
(schémas, service, router) ne plante pas hors Docker, faute des bibliothèques
natives (Pango, Cairo, GDK-Pixbuf) que seule l'image Docker installe. À
l'écriture de `rapports/pdf.py` pour l'étape 9, la question se repose
naturellement : cette contrainte tient-elle toujours, ou l'usage réel du
module justifie-t-il d'assouplir la règle ?

**Décision.** La contrainte est confirmée telle quelle : `import weasyprint`
reste strictement local à la fonction de génération (`generer_pdf(...)`
et équivalents), jamais en tête de `rapports/pdf.py`. Rien depuis l'ADR
d'origine ne change la donne — le poste de développement Windows de ce
projet n'a toujours pas le runtime GTK, et le report du coût d'import au
seul appel réel (au lieu de l'import du module) reste la façon la plus
simple de garder `rapports/service.py` et `rapports/router.py` testables et
important partout, y compris en dehors du conteneur.

**Conséquences.** Aucun changement de comportement par rapport à l'ADR
d'origine — celui-ci n'est pas remplacé, il est reconduit. Les tests
unitaires et d'intégration qui n'exercent pas la génération PDF proprement
dite continuent de s'exécuter hors conteneur sans le runtime GTK ; seuls les
tests qui appellent réellement `generer_pdf(...)` doivent tourner dans
l'image Docker (ou une CI dotée des mêmes paquets système), comme prévu.

## 3. Détection du type MIME par signatures d'octets manuelles, pas par `python-magic`

**Contexte.** Le justificatif d'une charge (`shared/stockage.py`, étape 7)
n'accepte que trois types : JPEG, PNG, PDF. Deux options existaient pour
vérifier le type réel d'un fichier reçu : une bibliothèque dédiée
(`python-magic`, qui s'appuie sur `libmagic`, une dépendance système
supplémentaire à installer et maintenir dans l'image Docker) ou une
comparaison directe des premiers octets du fichier à la signature connue de
chacun des trois formats.

**Décision.** Comparaison manuelle des octets (`shared/stockage.py`,
`detecter_type_mime`) : JPEG commence par `FF D8 FF`, PNG par
`89 50 4E 47 0D 0A 1A 0A`, PDF par `%PDF-`. Trois signatures suffisent, le
code tient en quelques lignes, et il ne demande ni `libmagic` côté système
ni paquet Python supplémentaire côté application. `python-magic` se
justifierait pour une liste de types beaucoup plus longue ou évolutive ; ce
n'est pas le cas ici, le cahier des charges fixant la liste à trois formats
pour la durée de vie prévisible du projet.

**Conséquences.** Une dépendance système en moins dans l'image Docker du
backend (pas de `libmagic1` à installer, contrairement à WeasyPrint qui en
demande plusieurs). Si un futur besoin élargit la liste des formats acceptés
au-delà de JPEG/PNG/PDF, `python-magic` redeviendra une option à réévaluer —
mais ajouter une signature de plus à `_SIGNATURES` restera presque toujours
suffisant tant que la liste reste courte et les formats bien définis.
