# Tarifs professeurs réservés à l'administrateur

## Contexte

Les tarifs professeurs (`montant_par_eleve_cents` par matière/niveau) étaient
lisibles par le rôle CAISSIER au même titre que les tarifs élève, sur le même
principe de lecture élargie que le reste du référentiel. Contrairement au
tarif élève — que le caissier doit connaître pour encaisser une mensualité —,
le tarif professeur ne sert à aucune tâche de caisse : il ne fait que révéler
combien le centre reverse par élève à chaque professeur, donc sa marge brute
par matière/niveau. Une information de gestion, pas une information de guichet.

## Décision

`GET /referentiel/tarifs-professeur` passe de `exige_role(ADMIN, CAISSIER)` à
`exige_role(ADMIN)`, aligné sur les routes d'écriture qui étaient déjà
ADMIN-seules. Les tarifs élève ne changent pas : le caissier garde une lecture
complète. Côté front, la section « Tarif professeur » de `/referentiel/tarifs`
ne s'affiche plus pour CAISSIER (la section « Tarif élève » reste visible) —
un seul écran, pas une page dédiée à masquer entièrement.
