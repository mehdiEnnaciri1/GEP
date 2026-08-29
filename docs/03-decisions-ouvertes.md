# GEP — Décisions à valider avant de coder

Chaque point ci-dessous a une valeur par défaut déjà implémentée dans le modèle de
données. Il faut les confirmer avec le responsable du centre, parce que revenir dessus
après la mise en production coûte une migration de données financières.

Les décisions D1 à D4 sont **bloquantes** : elles déterminent le schéma.

---

## D1 — Figeage des tarifs *(bloquante)*

**Ce que dit le CDC.** §6 : « Ce tableau doit être modifiable par l'administrateur. »
Rien sur l'effet d'une modification sur le passé.

**Le problème.** Si le tarif 2BAC-Physique passe de 35 à 40 DH en janvier et que la paie
se recalcule à la volée, la paie de décembre passe de 630 à 720 DH. Un professeur déjà
payé voit son historique changer. Idem côté élève : augmenter un tarif transformerait
des mois soldés en impayés.

**Décision retenue.** Le tarif est **copié** au moment de l'engagement, dans
`inscription_matiere.tarif_mensuel_cents` et dans `ligne_paie.tarif_unitaire_cents`. Une
modification du référentiel ne s'applique qu'aux engagements futurs.

**Question au client.** Quand vous augmentez un tarif, les élèves déjà inscrits paient-ils
l'ancien ou le nouveau à partir du mois suivant ? Le modèle permet les deux : conserver
l'inscription (ancien tarif maintenu) ou la clôturer et en rouvrir une (nouveau tarif dès
le mois suivant). Il faut savoir si l'interface doit proposer une action « appliquer le
nouveau tarif aux élèves existants ».

---

## D2 — Double comptage dans le bénéfice net *(bloquante)*

**Ce que dit le CDC.** §9 :
`Bénéfice net = Encaissements totaux + Total des frais d'inscription – Charges – Paie`

**Le problème.** Les 50 DH d'inscription sont un encaissement. S'ils figurent dans
« encaissements totaux », les ajouter une seconde fois surévalue le bénéfice de 50 DH par
nouvel élève. Sur une rentrée à 80 inscriptions, l'écart est de 4 000 DH.

Le §9 contient par ailleurs :
`Montant des frais d'inscription cumulées = Somme des frais – les charges mensuelles`
qui n'a pas de sens (des frais cumulés ne se définissent pas par soustraction des
charges) et est traité comme une erreur de rédaction.

**Décision retenue.** `paiement.type` vaut `MENSUALITE` ou `INSCRIPTION`. Les deux
ensembles sont disjoints, la somme est donc exacte. Le dashboard affiche les deux lignes
séparément.

**Question au client.** Confirmer que le bénéfice net doit bien inclure les frais
d'inscription. Comptablement, des frais d'inscription sont un produit d'exploitation, donc
oui — mais autant l'entendre dire.

---

## D3 — Un seul professeur par (matière, niveau) *(bloquante)*

**Ce que dit le CDC.** §7.1 :
`Rémunération = Tarif professeur par élève × Nombre d'élèves inscrits dans cette matière et ce niveau`

**Le problème.** La formule ne mentionne pas le professeur dans le comptage. Si M. Ahmed
et M. Karim enseignent tous deux les maths en 2BAC avec 30 élèves au total, chacun est
payé 30 × 35 = 1 050 DH. Le centre verse 2 100 DH pour 30 élèves. La formule n'est bien
définie **que** s'il y a un professeur par couple (matière, niveau).

**Décision retenue.** Contrainte `UNIQUE (annee_scolaire_id, matiere_id, niveau_code)` sur
`affectation`. Le cas est rendu impossible en base plutôt que de produire une paie fausse
sans alerte.

**Question au client.** Arrive-t-il qu'un même niveau et une même matière soient assurés
par deux professeurs (deux groupes, deux créneaux) ? Si oui, il faut la notion de groupe
dès la v1, et non en évolution future — la répartition des élèves par groupe devient alors
la base du calcul de paie. C'est un ajout d'environ deux tables et une refonte du calcul :
important à savoir maintenant.

---

## D4 — Le professeur est-il payé sur les impayés ? *(bloquante)*

**Ce que dit le CDC.** « Nombre d'élèves **inscrits** dans cette matière et ce niveau. »

**Le problème.** Littéralement, le professeur est payé pour un élève qui n'a jamais réglé.
C'est défendable — le cours a été donné — mais c'est une décision de gestion, pas une
évidence technique, et elle a un impact direct sur la trésorerie du centre.

**Décision retenue.** Paramètre `base_calcul_paie`, valeur par défaut `inscrits`
(lecture littérale du CDC). L'alternative `payants` ne compterait que les élèves dont
l'échéance du mois est `PAYE` ou `PARTIEL`.

**Question au client.** Un élève inscrit en maths qui n'a pas payé le mois de novembre
compte-t-il dans la paie du professeur de novembre ? Et un élève suspendu en cours de mois ?

---

## D5 — L'année scolaire

**Ce que dit le CDC.** Rien. La dimension est absente du document.

**Le problème.** Sans elle : un élève reste en 1AC indéfiniment, on ne peut pas comparer
deux rentrées, les tarifs n'ont pas de portée temporelle, et le passage de niveau en
septembre efface l'historique du niveau précédent.

**Décision retenue.** Table `annee_scolaire`, référencée par `eleve`, `tarif_eleve`,
`tarif_professeur` et `affectation`. Une seule année active à la fois.

**Question au client.** L'année scolaire va-t-elle de septembre à juin, ou de septembre à
juillet (avec cours d'été) ? Et faut-il une procédure de passage à l'année suivante
(reconduire les élèves en montant leur niveau d'un cran, avec dispense de frais
d'inscription) ? Je recommande fortement de l'inclure — sinon la rentrée 2026 se fera par
ressaisie manuelle de tous les élèves.

---

## D6 — Génération des échéances mensuelles

**Ce que dit le CDC.** §4.2 demande « montant restant à payer » et « liste des élèves en
retard de paiement », sans dire comment le montant dû est établi.

**Décision retenue.** Génération automatique le 1er de chaque mois d'une `echeance` par
élève actif, à partir de ses inscriptions. Le calcul à la volée serait plus simple mais
rendrait l'historique instable : modifier les inscriptions d'un élève changerait
rétroactivement ce qu'il devait il y a six mois.

**Question au client.** Un élève inscrit le 20 octobre doit-il le mois d'octobre en entier,
la moitié, ou rien ? Trois règles possibles : mois entier quelle que soit la date, prorata
au jour, ou facturation à partir du mois suivant. Par défaut : **mois entier** (usage le
plus répandu dans les centres de soutien, et le plus simple à expliquer à un parent).

---

## D7 — Paiement bloquant à l'inscription

**Ce que dit le CDC.** §3.1 : « L'élève ne peut être considéré comme inscrit définitivement
que lorsque les frais d'inscription sont payés. »

**Décision retenue.** L'élève est créé avec `statut = ACTIF` et une ligne
`frais_inscription` en `NON_PAYE`. L'interface affiche un bandeau d'alerte tant que le
paiement n'est pas enregistré, et un rapport liste les inscriptions incomplètes.

**Question au client.** Que signifie concrètement « pas inscrit définitivement » ?
Trois options : l'élève existe mais est signalé (option retenue), l'élève est en statut
`SUSPENDU` et ne génère pas d'échéance, ou la création est purement impossible sans
paiement simultané. La troisième est rigide — une secrétaire doit pouvoir saisir un
dossier et encaisser dix minutes plus tard.

---

## D8 — Paiement couvrant plusieurs mois

**Ce que dit le CDC.** §4.1 : un paiement porte sur un « mois de paiement » unique.

**Le problème.** Un parent qui règle trois mois d'avance oblige à saisir trois paiements
distincts. C'est acceptable, mais il faut le savoir.

**Décision retenue.** Un paiement = un mois, conformément au CDC. L'interface propose une
saisie multi-mois qui crée plusieurs enregistrements en une transaction, avec un reçu
groupé.

**Question au client.** Les règlements trimestriels ou annuels sont-ils courants ? Si oui,
faut-il un tarif préférentiel dans ce cas ? Une remise changerait le modèle (il faudrait
une notion de réduction sur l'échéance).

> **Mise à jour 2026-08-29.** La notion de réduction évoquée ici est arrivée par un autre
> chemin — pas un tarif préférentiel sur un règlement groupé, mais un montant mensuel fixe
> par élève (`mode_facturation`). Voir `docs/adr/2026-08-29-pack-et-reduction.md`. La
> question du règlement trimestriel/annuel elle-même reste ouverte.

---

## D9 — Élève changeant de niveau en cours d'année

**Ce que dit le CDC.** Rien.

**Le problème.** Un élève qui passe de 1BAC à 2BAC en cours d'année change de tarif élève,
de tarif professeur, et bascule d'une affectation à une autre. Le calcul de paie du mois
concerné devient ambigu.

**Décision retenue.** Le niveau est une colonne modifiable de `eleve`, et le changement
est journalisé dans `journal_audit`. La paie du mois utilise le niveau tel qu'il est à la
date de génération.

**Question au client.** Est-ce un cas réel ? Si c'est fréquent, il faudrait historiser le
niveau (table `historique_niveau`) plutôt qu'une simple colonne.

---

## Récapitulatif

| # | Sujet | Défaut retenu | Bloquante |
|---|---|---|---|
| D1 | Figeage des tarifs | Copie à l'engagement | Oui |
| D2 | Double comptage inscription | Types de paiement disjoints | Oui |
| D3 | Un prof par (matière, niveau) | Contrainte d'unicité | Oui |
| D4 | Paie sur inscrits ou payants | `inscrits` | Oui |
| D5 | Année scolaire | Table dédiée, une active | Non, mais recommandée |
| D6 | Facturation du mois d'entrée | Mois entier | Non |
| D7 | Blocage frais d'inscription | Alerte, pas blocage | Non |
| D8 | Paiement multi-mois | N enregistrements, reçu groupé | Non |
| D9 | Changement de niveau | Colonne modifiable + audit | Non |
