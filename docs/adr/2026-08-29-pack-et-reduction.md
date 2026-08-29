# Facturation par forfait (pack) et montant personnalisé (réduction)

## Contexte

Cette demande touche une question déjà signalée comme ouverte dans D8
(`docs/03-decisions-ouvertes.md`) : « une remise changerait le modèle, il
faudrait une notion de réduction sur l'échéance ». Le §8.1 du modèle de
données ne connaît qu'un seul mode de calcul du montant dû mensuel : la somme
des tarifs des matières inscrites. Deux besoins, désormais fixés par D10 et
D11 (`docs/03-decisions-ouvertes.md`) :

- **Pack** : un élève qui prend toutes les matières d'un niveau paie un
  forfait, pas la somme des tarifs individuels.
- **Réduction** : un montant mensuel fixe, saisi à la main, remplace le calcul
  pour un élève donné, pour toute l'année scolaire.

Dans les deux cas, la rémunération des professeurs ne doit **rien** changer :
elle reste calculée matière par matière, sur les mêmes `inscription_matiere`
et les mêmes `tarif_professeur` qu'aujourd'hui — voir D10 sur ce point
précis.

## Décision

**Le pack désigne littéralement toutes les matières tarifées du niveau.** Un
élève en pack a une `inscription_matiere` réelle par matière (`matiere_id`
NOT NULL comme toute inscription), visible et comptée normalement par chaque
professeur — le pack n'est qu'un mode de tarification côté élève, jamais un
type d'inscription à part. Le tarif de chaque inscription est le forfait
pack fractionné à parts égales entre les matières (division entière, le
reste en centimes va à la matière de plus petit id) — la somme des
inscriptions retombe donc exactement sur le forfait.

`eleve.est_pack BOOLEAN` marque le mode. Le prix du forfait est un montant
fixe par (année, niveau) dans une table dédiée `tarif_pack` — copié dans les
inscriptions à l'engagement, jamais recalculé après coup (même principe D1
que `tarif_eleve`) : modifier le tarif pack du référentiel ne change rien
aux élèves déjà en pack.

**La réduction ne touche à aucune inscription.** `eleve.reduction_mensuelle_cents`
(NULL = pas de réduction) est un montant fixe saisi à la main, copié tel
quel, sans référence au référentiel. L'élève choisit ses matières comme en
facturation normale — ces inscriptions réelles servent à la paie
professeur, seul le calcul de l'échéance de l'élève les ignore.

**Pack et réduction sont mutuellement exclusifs** (contrainte
`ck_eleve_pack_reduction_exclusifs`) : un élève est soit en facturation
normale, soit en pack, soit en réduction, jamais deux à la fois.

Le montant dû mensuel (§8.1) devient :

```
si reduction_mensuelle_cents IS NOT NULL : reduction_mensuelle_cents
sinon                                    : Σ inscription_matiere.tarif_mensuel_cents
```

Aucune branche spéciale pour le pack dans cette formule : ses inscriptions
portent déjà le tarif fractionné, la somme suffit.

**Échéance et `ligne_echeance`.** En réduction, une seule `ligne_echeance`
est écrite (montant = la réduction), rattachée à la première matière suivie
(par id) pour satisfaire la clé étrangère — elle ne prétend pas répartir le
montant par matière, c'est un simple ancrage. Sinon (normal ou pack), une
ligne par matière au tarif figé, comme avant.

**Activation/désactivation après création.** Activer le pack clôture les
inscriptions en cours et en recrée une par matière tarifée du niveau, au
tarif fractionné. Désactiver le pack clôture les inscriptions sans en
recréer — une nouvelle inscription individuelle est un acte séparé. La
réduction s'active/se désactive sans toucher aux inscriptions. Ces deux
opérations sont ouvertes à ADMIN et CAISSIER (comme la création d'élève).
