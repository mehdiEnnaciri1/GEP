# Facturation par forfait (pack) et montant personnalisé (réduction)

## Contexte

Cette demande touche une question déjà signalée comme ouverte dans D8
(`docs/03-decisions-ouvertes.md`) : « une remise changerait le modèle, il
faudrait une notion de réduction sur l'échéance ». Le §8.1 du modèle de
données ne connaît qu'un seul mode de calcul du montant dû mensuel : la somme
des tarifs des matières inscrites. Deux nouveaux besoins, tranchés après
clarification avec l'utilisateur :

- **Pack** : un élève qui prend toutes les matières d'un niveau paie un
  forfait, pas la somme des tarifs individuels.
- **Réduction** : un montant mensuel fixe, saisi à la main, remplace le calcul
  pour un élève donné, pour toute l'année scolaire.

Dans les deux cas, la rémunération des professeurs ne doit **rien** changer :
elle reste calculée matière par matière, sur les mêmes `inscription_matiere`
et les mêmes `tarif_professeur` qu'aujourd'hui.

## Décision

Nouvelle colonne `eleve.mode_facturation` (`NORMAL` | `PACK` |
`PERSONNALISE`, défaut `NORMAL`) et `eleve.montant_mensuel_fixe_cents`
(NULL en `NORMAL`, obligatoire sinon — contrainte `CHECK` en base). Les deux
modes non-`NORMAL` sont mutuellement exclusifs et remplacent entièrement le
mode `NORMAL`, pas cumulables (choix retenu après clarification). Le montant
dû mensuel (§8.1) devient :

```
si mode_facturation = NORMAL : Σ inscription_matiere.tarif_mensuel_cents
sinon                        : eleve.montant_mensuel_fixe_cents
```

**Pack.** « Toutes les matières du niveau » n'a pas de définition native dans
ce modèle — les matières ne sont pas rattachées à un niveau, seul un tarif
`tarif_eleve(niveau, matière)` les relie. Le pack se compose donc de toutes
les matières ayant un tarif pour ce niveau. Une `inscription_matiere` réelle
est créée pour chacune, avec son vrai tarif — c'est ce qui garantit que la
paie professeur (comptage par matière/niveau) n'est pas affectée. Le prix du
pack est un montant fixe par (année, niveau), saisi par l'admin dans une
nouvelle table `tarif_pack` (même principe D1 que `tarif_eleve` : copié à
l'engagement dans `montant_mensuel_fixe_cents`, jamais recalculé après coup).

**Réduction.** Le montant est saisi directement à la création de l'élève et
copié tel quel dans `montant_mensuel_fixe_cents` — pas de notion de
pourcentage ni de référence au référentiel. L'élève choisit ses matières
normalement (comme en mode `NORMAL`), pour que la paie professeur reste
correcte.

Les deux modes se choisissent uniquement à la création de l'élève dans cette
version — pas de changement de mode a posteriori sur un élève existant.
