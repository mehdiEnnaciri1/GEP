# Indicateur « marge hors loyer » au dashboard

## Contexte

La demande initiale formulait « frais_cumules = somme des frais − (charges −
loyer) » — une formule qui n'a pas de sens comptable telle quelle : des frais
d'inscription cumulés sont une somme d'encaissements, on n'en soustrait pas
des charges. Après clarification, l'intention réelle est un indicateur de
couverture distinct du bénéfice net : dans quelle mesure les frais
d'inscription du mois couvrent les charges hors loyer — le loyer étant la
charge la plus prévisible et la moins pilotable au jour le jour, l'isoler
donne une lecture différente de la santé financière du mois que le bénéfice
net brut.

## Décision

Nouvel indicateur `marge_hors_loyer_cents`, ADMIN seul (même endpoint
`/dashboard/complet`), calculé comme
`frais_inscription_cents − (total_charges_cents − total_loyer_cents)`. Le
loyer est identifié par la catégorie de charge de libellé exact `"Loyer"`
(seed de `app/db/seeds.py`) — pas de colonne dédiée sur `charge` ou
`categorie_charge`, ce libellé est la seule clé stable disponible aujourd'hui.
Le loyer continue de compter normalement dans `total_charges_cents` et
`benefice_net_cents` : ce nouvel indicateur s'ajoute à côté, il ne remplace
rien.
