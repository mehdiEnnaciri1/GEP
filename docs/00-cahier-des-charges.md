**Cahier des charges**

**Site web de gestion des élèves, des paiements et de la paie des professeurs**

Table des matières

	1. Contexte du projet	2

	2. Niveaux scolaires gérés	2

	3. Gestion des élèves	2

	3.1 Création d’un élève	2

	3.2 Choix des matières	3

	4. Suivi des paiements des élèves	3

	4.1 Enregistrement d’un paiement	3

	4.2 Consultation des paiements	3

	5. Gestion des professeurs	4

	5.1 Création d’un professeur	4

	5.2 Affectation des niveaux	4

	6. Tableau des tarifs des professeurs	4

	7. Calcul de la rémunération des professeurs	5

	7.1 Règle de calcul	5

	7.2 Calcul mensuel	5

	8. Gestion des charges mensuelles du centre	6

	8.1 Types de charges	6

	8.2 Enregistrement d’une charge	6

	8.3 Consultation des charges	6

	9. Tableau de bord (Dashboard)	7

	10. Rapports et impressions	7

	11. Gestion des utilisateurs	8

	12. Évolutions futures souhaitées	8

	13. Résumé du flux principal	9

1. Contexte du projet

Le centre de soutien scolaire souhaite mettre en place une application web permettant de gérer :

- L’inscription des élèves par niveau scolaire,

- Les matières suivies par chaque élève,

- Le suivi des paiements des élèves,

- L’affectation des professeurs,

- Le calcul automatique de la rémunération des professeurs.

- Suivie des charges du centre

L’objectif est de centraliser les informations administratives et financières du centre afin de réduire les erreurs de calcul et de faciliter le suivi quotidien.

2. Niveaux scolaires gérés

Le système doit gérer les niveaux suivants :

- 1AC

- 2AC

- 3AC

- TC

- 1BAC

- 2BAC

3. Gestion des élèves

3.1 Création d’un élève

Pour chaque élève, le système doit permettre de saisir :

- Nom 

- Prénom

- Téléphone de l’élève (optionnel)

- Téléphone du parent/tuteur

- Niveau scolaire

- Date d’inscription

- Statut (Actif / Suspendu / Archivé)

- Lors de l’inscription d’un nouvel élève, le système doit obligatoirement enregistrer le paiement des frais d’inscription fixés à 50 DH.

- Montant fixe : 50 DH

- Payable une seule fois lors de la première inscription de l’élève

- L’élève ne peut être considéré comme inscrit définitivement que lorsque les frais d’inscription sont payés

- Statut de paiement des frais d’inscription : Payé / Non payé

3.2 Choix des matières

Un élève peut être inscrit à une ou plusieurs matières.

Exemples de matières :

- Mathématiques

- Physique-Chimie

- Français

- Anglais

- Arabe

- SVT

Pour chaque matière, le système doit enregistrer :

- La matière choisie,

- Le tarif mensuel de la matière pour ce niveau.

4. Suivi des paiements des élèves

Le système doit permettre :

4.1 Enregistrement d’un paiement

	- Élève concerné

	- Mois de paiement

	- Montant payé

	- Date de paiement

	- Mode de paiement (Espèces, Virement, etc.)

	- Observation (optionnel)

4.2 Consultation des paiements

	- Historique des paiements par élève

	- Liste des élèves en retard de paiement

	- Montant restant à payer

	- État : Payé / Partiellement payé / Non payé

5. Gestion des professeurs

5.1 Création d’un professeur

Informations à enregistrer :

	- Nom et prénom

	- Téléphone

	- Matière enseignée

	- Niveaux affectés (un ou plusieurs)

5.2 Affectation des niveaux

Un professeur peut être affecté :

	- À un seul niveau,

	- Ou à plusieurs niveaux.

Exemple :

| Professeur | Matière | Niveaux |
| --- | --- | --- |
| M. Ahmed | Mathématiques | 1BAC, 2BAC |
| Mme Sara | Français | 1AC, 2AC, 3AC |

6. Tableau des tarifs des professeurs

Le système doit contenir un tableau de référence indiquant le tarif par élève en fonction de la matière et du niveau.

**Exemple**

| **Niveau** | **Matière** | **Tarif professeur / élève (DH)** |
| --- | --- | --- |
| 1AC | Mathématiques | 20 |
| 1AC | Français | 15 |
| 2BAC | Physique | 35 |

Ce tableau doit être modifiable par l’administrateur.

7. Calcul de la rémunération des professeurs

7.1 Règle de calcul

Pour chaque matière et niveau :

Rémunération = Tarif professeur par élève × Nombre d’élèves inscrits dans cette matière et ce niveau

**Exemple**

		- Niveau : 2BAC

		- Matière : Physique

		- Tarif professeur : 35 DH / élève

		- Nombre d’élèves : 18

Rémunération = 35 × 18 = 630 DH

7.2 Calcul mensuel

Le système doit générer automatiquement la paie mensuelle de chaque professeur en additionnant toutes ses affectations.

**Exemple**

| **Niveau** | **Matière** | **Élèves** | **Montant** |
| --- | --- | --- | --- |
| 1BAC | Math | 12 | 300 DH |
| 2BAC | Math | 15 | 450 DH |
| Total | 750 DH |

8. Gestion des charges mensuelles du centre

Le système doit permettre de gérer les charges mensuelles du centre afin de connaître le bénéfice réel après paiement des dépenses.

8.1 Types de charges

L’administrateur doit pouvoir créer et modifier les catégories de charges, par exemple :

- Loyer

- Électricité

- Eau

- Internet

- Salaires administratifs

- Fournitures

- Entretien

- Publicité / Marketing

- Autres charges

8.2 Enregistrement d’une charge

Pour chaque charge, le système doit enregistrer :

- Catégorie

- Description

- Montant

- Date

- Mois concerné

- Mode de paiement

- Pièce justificative (optionnelle : photo ou PDF)

8.3 Consultation des charges

Le système doit permettre :

- Liste des charges par mois

- Total des charges mensuelles

- Total par catégorie

- Historique des charges

9. Tableau de bord (Dashboard)

**Administrateur**

Le tableau de bord doit afficher :

- Nombre total d’élèves

- Nombre d’élèves par niveau

- Montant total encaissé du mois

- Montant des frais d’inscription cumulées 

- Montant des frais d’inscription cumulées = Somme des frais – les charges mensuelles 

- Montant des impayés

- Nombre de professeurs

- Tableau contient le Total des charges par chaque mois

- Tableau contient paiement des professeurs par chaque mois

- Bénéfice net du mois

- Formule du bénéfice net : 

- Bénéfice net = Encaissements totaux + Total des frais d’inscription – Charges mensuelles – Paie des professeurs

10. Rapports et impressions

Le système doit permettre d’exporter en PDF et Excel :

- Liste des élèves

- Liste des paiements

- Liste des impayés

- Paie des professeurs

- Récapitulatif mensuel du centre

11. Gestion des utilisateurs

**Rôles**

**Administrateur**

- Accès complet

- Gestion des tarifs

- Gestion des élèves

- Gestion des professeurs

- Validation des paiements

**Caissier/Secrétaire**

- Gestion des élèves

- Enregistrement des paiements

**Professeur (optionnel)**

- Consultation uniquement

12. Évolutions futures souhaitées

- Gestion des groupes et horaires

- Pointage des présences

- Envoi de SMS/WhatsApp pour les rappels de paiement

- Signature électronique des reçus

- Application mobile Android

13. Résumé du flux principal

- Inscription élève

- Choix du niveau

- Choix des matières

- Paiement mensuel

- Comptage des élèves par matière

- Calcul automatique de la paie professeur