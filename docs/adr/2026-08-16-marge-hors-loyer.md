# Frais d'inscription cumulés nets du loyer (ADMIN)

## Contexte

La demande initiale formulait « frais_cumules = somme des frais − (charges −
loyer) » — une formule qui n'a pas de sens comptable si on l'applique
littéralement à « frais d'inscription cumulés » (une somme d'encaissements,
on n'en soustrait pas des charges). Une première version a donc introduit un
indicateur séparé, `marge_hors_loyer_cents`, à côté du bénéfice net.

**Révision.** L'utilisateur a demandé la suppression de cet indicateur
séparé et l'application directe de la formule au champ « Frais d'inscription
cumulés » existant. Ce champ (`montant_frais_inscription_cumules_cents`) est
visible par CAISSIER *et* ADMIN (`IndicateursRestreints`, hérité par
`IndicateursComplets`) — or le calcul demandé repose sur les charges, que le
CAISSIER n'a jamais le droit de voir (§6.6 : « ni charges, ni bénéfice net,
ni paie »). Impossible de changer ce champ pour tout le monde sans lui faire
révéler indirectement des charges.

## Décision

Le champ garde son nom, `montant_frais_inscription_cumules_cents`, mais son
calcul diverge désormais selon le rôle :

- **CAISSIER** (`IndicateursRestreints`) : somme brute des encaissements de
  type `INSCRIPTION`, inchangée.
- **ADMIN** (`IndicateursComplets`) : `frais_inscription_cents −
  (total_charges_cents − total_loyer_cents)` — la formule demandée, avec le
  loyer explicitement exclu des charges retranchées.

Le loyer est identifié par la catégorie de charge de libellé exact `"Loyer"`
(seed de `app/db/seeds.py`) — pas de colonne dédiée sur `charge` ou
`categorie_charge`, ce libellé est la seule clé stable disponible
aujourd'hui. Le loyer continue de compter normalement dans
`total_charges_cents` et `benefice_net_cents`, tous deux ADMIN seuls et
inchangés par cette décision.

Une même clé JSON portant deux calculs différents selon le rôle est
inhabituel dans ce projet — le compromis retenu ici plutôt que d'exposer au
CAISSIER une donnée dérivée des charges.
