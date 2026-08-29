# GEP — Modèle de données

Toutes les tables sont en PostgreSQL 16. Le DDL ci-dessous est la **référence** ;
l'implémentation réelle passe par des modèles SQLAlchemy et des migrations Alembic.

Conventions :
- Montants : `BIGINT`, en **centimes de dirham**. Jamais de flottant.
- Horodatages : `TIMESTAMPTZ`, en UTC.
- Périodes mensuelles : `CHAR(7)` au format `YYYY-MM`.
- Clés primaires : `BIGSERIAL`, sauf `niveau` qui utilise son code métier.
- Toute table a `cree_le`, `modifie_le`. Les tables financières ont en plus `cree_par`.

---

## 1. Socle et référentiel

### annee_scolaire

Dimension absente du cahier des charges, ajoutée délibérément. Sans elle, impossible
de comparer deux rentrées, de faire évoluer les tarifs d'une année sur l'autre, ni de
faire passer un élève de 1AC à 2AC en conservant son historique.

```sql
CREATE TABLE annee_scolaire (
    id           BIGSERIAL PRIMARY KEY,
    libelle      VARCHAR(9)  NOT NULL UNIQUE,   -- '2025-2026'
    date_debut   DATE        NOT NULL,
    date_fin     DATE        NOT NULL,
    est_active   BOOLEAN     NOT NULL DEFAULT FALSE,
    cree_le      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_annee_dates CHECK (date_fin > date_debut)
);

-- Une seule année active à la fois
CREATE UNIQUE INDEX ux_annee_active ON annee_scolaire (est_active) WHERE est_active;
```

### niveau

Table de référence figée par le cahier des charges (§2). `ordre` sert au tri
d'affichage et à la logique de passage de niveau.

```sql
CREATE TABLE niveau (
    code    VARCHAR(5) PRIMARY KEY,   -- 1AC, 2AC, 3AC, TC, 1BAC, 2BAC
    libelle VARCHAR(60) NOT NULL,
    ordre   SMALLINT    NOT NULL UNIQUE
);

INSERT INTO niveau (code, libelle, ordre) VALUES
  ('1AC',  '1ère année collège',      1),
  ('2AC',  '2ème année collège',      2),
  ('3AC',  '3ème année collège',      3),
  ('TC',   'Tronc commun',            4),
  ('1BAC', '1ère année baccalauréat', 5),
  ('2BAC', '2ème année baccalauréat', 6);
```

### matiere

```sql
CREATE TABLE matiere (
    id      BIGSERIAL PRIMARY KEY,
    code    VARCHAR(20) NOT NULL UNIQUE,
    libelle VARCHAR(80) NOT NULL,
    actif   BOOLEAN     NOT NULL DEFAULT TRUE,
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Mathématiques, Physique-Chimie, Français, Anglais, Arabe, SVT
```

### parametre

Ce que le cahier des charges donne comme constante mais qui changera : les frais
d'inscription de 50 DH, la règle de comptage pour la paie, le nom du centre sur les reçus.

```sql
CREATE TABLE parametre (
    cle         VARCHAR(60) PRIMARY KEY,
    valeur      TEXT        NOT NULL,
    type_valeur VARCHAR(10) NOT NULL,   -- 'entier' | 'texte' | 'booleen'
    description TEXT,
    modifie_le  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO parametre (cle, valeur, type_valeur, description) VALUES
  ('frais_inscription_cents', '5000',   'entier',  'Frais d''inscription en centimes (50 DH)'),
  ('base_calcul_paie',        'inscrits','texte',  'inscrits | payants — voir décision D4'),
  ('nom_centre',              'Centre', 'texte',   'Affiché sur les reçus et rapports');
```

### tarif_eleve

Ce que l'élève paie par mois, par matière et par niveau (§3.2).

```sql
CREATE TABLE tarif_eleve (
    id                BIGSERIAL PRIMARY KEY,
    annee_scolaire_id BIGINT     NOT NULL REFERENCES annee_scolaire(id),
    niveau_code       VARCHAR(5) NOT NULL REFERENCES niveau(code),
    matiere_id        BIGINT     NOT NULL REFERENCES matiere(id),
    montant_cents     BIGINT     NOT NULL,
    cree_le           TIMESTAMPTZ NOT NULL DEFAULT now(),
    modifie_le        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tarif_eleve_positif CHECK (montant_cents >= 0),
    CONSTRAINT ux_tarif_eleve UNIQUE (annee_scolaire_id, niveau_code, matiere_id)
);
```

### tarif_pack

Forfait couvrant toutes les matières tarifées d'un niveau — voir
`docs/adr/2026-08-29-pack-et-reduction.md` (D10). Clé (année, niveau)
seulement, pas de matière : un seul montant par niveau, pas un croisement.

```sql
CREATE TABLE tarif_pack (
    id                BIGSERIAL PRIMARY KEY,
    annee_scolaire_id BIGINT     NOT NULL REFERENCES annee_scolaire(id),
    niveau_code       VARCHAR(5) NOT NULL REFERENCES niveau(code),
    montant_cents     BIGINT     NOT NULL,
    cree_le           TIMESTAMPTZ NOT NULL DEFAULT now(),
    modifie_le        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tarif_pack_positif CHECK (montant_cents >= 0),
    CONSTRAINT ux_tarif_pack UNIQUE (annee_scolaire_id, niveau_code)
);
```

### tarif_professeur

Ce que le centre verse au professeur **par élève**, par matière et par niveau (§6).

```sql
CREATE TABLE tarif_professeur (
    id                    BIGSERIAL PRIMARY KEY,
    annee_scolaire_id     BIGINT     NOT NULL REFERENCES annee_scolaire(id),
    niveau_code           VARCHAR(5) NOT NULL REFERENCES niveau(code),
    matiere_id            BIGINT     NOT NULL REFERENCES matiere(id),
    montant_par_eleve_cents BIGINT   NOT NULL,
    cree_le               TIMESTAMPTZ NOT NULL DEFAULT now(),
    modifie_le            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tarif_prof_positif CHECK (montant_par_eleve_cents >= 0),
    CONSTRAINT ux_tarif_prof UNIQUE (annee_scolaire_id, niveau_code, matiere_id)
);
```

> **Deux tables distinctes, volontairement.** Le tarif élève et le tarif professeur
> portent sur la même clé (année, niveau, matière) mais n'ont ni la même unité
> (forfait mensuel contre montant par élève), ni le même propriétaire fonctionnel, ni
> le même rythme de révision. Les fusionner créerait une table à deux colonnes de
> montant dont l'une est toujours mal comprise.

---

## 2. Utilisateurs

```sql
CREATE TYPE role_utilisateur AS ENUM ('ADMIN', 'CAISSIER', 'PROFESSEUR');

CREATE TABLE utilisateur (
    id                BIGSERIAL PRIMARY KEY,
    nom               VARCHAR(80)  NOT NULL,
    prenom            VARCHAR(80)  NOT NULL,
    email             VARCHAR(160) NOT NULL UNIQUE,
    mot_de_passe_hash TEXT         NOT NULL,       -- Argon2id
    role              role_utilisateur NOT NULL,
    professeur_id     BIGINT       REFERENCES professeur(id),  -- si role = PROFESSEUR
    actif             BOOLEAN      NOT NULL DEFAULT TRUE,
    derniere_connexion TIMESTAMPTZ,
    cree_le           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_prof_lie CHECK (
        (role = 'PROFESSEUR' AND professeur_id IS NOT NULL)
        OR (role <> 'PROFESSEUR' AND professeur_id IS NULL)
    )
);
```

---

## 3. Élèves

```sql
CREATE TYPE statut_eleve AS ENUM ('ACTIF', 'SUSPENDU', 'ARCHIVE');

CREATE TABLE eleve (
    id                BIGSERIAL PRIMARY KEY,
    matricule         VARCHAR(20)  NOT NULL UNIQUE,   -- généré : E-2025-0001
    nom               VARCHAR(80)  NOT NULL,
    prenom            VARCHAR(80)  NOT NULL,
    telephone_eleve   VARCHAR(20),                    -- optionnel (§3.1)
    telephone_parent  VARCHAR(20)  NOT NULL,          -- obligatoire (§3.1)
    niveau_code       VARCHAR(5)   NOT NULL REFERENCES niveau(code),
    annee_scolaire_id BIGINT       NOT NULL REFERENCES annee_scolaire(id),
    date_inscription  DATE         NOT NULL,
    statut            statut_eleve NOT NULL DEFAULT 'ACTIF',
    -- Pack et réduction (D10, D11 — voir docs/adr/2026-08-29-pack-et-reduction.md) :
    -- mutuellement exclusifs, jamais les deux en même temps.
    est_pack                  BOOLEAN NOT NULL DEFAULT FALSE,
    reduction_mensuelle_cents BIGINT,   -- NULL = pas de réduction, sinon montant fixe copié
    observation       TEXT,
    cree_par          BIGINT       NOT NULL REFERENCES utilisateur(id),
    cree_le           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    modifie_le        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_eleve_reduction_positive
        CHECK (reduction_mensuelle_cents IS NULL OR reduction_mensuelle_cents >= 0),
    CONSTRAINT ck_eleve_pack_reduction_exclusifs
        CHECK (NOT (est_pack AND reduction_mensuelle_cents IS NOT NULL))
);

CREATE INDEX ix_eleve_niveau_annee ON eleve (annee_scolaire_id, niveau_code)
    WHERE statut = 'ACTIF';
CREATE INDEX ix_eleve_nom ON eleve (nom, prenom);
```

### inscription_matiere

Le lien élève ↔ matière, avec **le tarif figé** au moment de l'inscription.

```sql
CREATE TABLE inscription_matiere (
    id                  BIGSERIAL PRIMARY KEY,
    eleve_id            BIGINT     NOT NULL REFERENCES eleve(id),
    matiere_id          BIGINT     NOT NULL REFERENCES matiere(id),
    tarif_mensuel_cents BIGINT     NOT NULL,   -- ⚠ COPIE de tarif_eleve, pas une référence
    date_debut          DATE       NOT NULL,
    date_fin            DATE,                  -- NULL = en cours
    cree_par            BIGINT     NOT NULL REFERENCES utilisateur(id),
    cree_le             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_insc_dates CHECK (date_fin IS NULL OR date_fin >= date_debut),
    CONSTRAINT ck_insc_tarif CHECK (tarif_mensuel_cents >= 0)
);

-- Un élève ne peut avoir qu'une inscription EN COURS par matière
CREATE UNIQUE INDEX ux_inscription_active
    ON inscription_matiere (eleve_id, matiere_id) WHERE date_fin IS NULL;
```

> **Pourquoi copier le tarif ?** Le §6 autorise l'administrateur à modifier les tarifs.
> Si l'inscription pointait vers `tarif_eleve`, augmenter le tarif de 200 à 250 DH en
> janvier changerait rétroactivement ce que l'élève devait en octobre, et transformerait
> des mois soldés en impayés. La copie garantit qu'une modification de tarif ne s'applique
> qu'aux inscriptions futures.
>
> Pour appliquer un nouveau tarif à un élève existant : on clôture l'inscription
> (`date_fin`) et on en ouvre une nouvelle. L'historique reste exact.

---

## 4. Paiements

### frais_inscription

Les 50 DH du §3.1 : montant fixe, une seule fois par élève, bloquant pour
l'inscription définitive.

```sql
CREATE TYPE statut_frais AS ENUM ('NON_PAYE', 'PAYE');

CREATE TABLE frais_inscription (
    id             BIGSERIAL PRIMARY KEY,
    eleve_id       BIGINT       NOT NULL UNIQUE REFERENCES eleve(id),
    montant_cents  BIGINT       NOT NULL,      -- copie du paramètre à la création
    statut         statut_frais NOT NULL DEFAULT 'NON_PAYE',
    date_paiement  DATE,
    mode_paiement  VARCHAR(20),
    paiement_id    BIGINT       REFERENCES paiement(id),
    cree_le        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_frais_coherent CHECK (
        (statut = 'PAYE' AND date_paiement IS NOT NULL AND paiement_id IS NOT NULL)
        OR (statut = 'NON_PAYE' AND date_paiement IS NULL)
    )
);
```

La contrainte `UNIQUE (eleve_id)` traduit littéralement « payable une seule fois lors
de la première inscription ». Un élève qui revient l'année suivante ne repaie pas.

### echeance

Ce que l'élève **doit** pour un mois donné. Généré, pas saisi.

```sql
CREATE TYPE statut_echeance AS ENUM ('NON_PAYE', 'PARTIEL', 'PAYE');

CREATE TABLE echeance (
    id                BIGSERIAL PRIMARY KEY,
    eleve_id          BIGINT      NOT NULL REFERENCES eleve(id),
    periode           CHAR(7)     NOT NULL,   -- '2025-10'
    montant_du_cents  BIGINT      NOT NULL,
    montant_paye_cents BIGINT     NOT NULL DEFAULT 0,
    statut            statut_echeance NOT NULL DEFAULT 'NON_PAYE',
    genere_le         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_echeance UNIQUE (eleve_id, periode),
    CONSTRAINT ck_periode_format CHECK (periode ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_echeance_montants CHECK (montant_du_cents >= 0 AND montant_paye_cents >= 0)
);

CREATE INDEX ix_echeance_impayes ON echeance (periode, statut)
    WHERE statut <> 'PAYE';
```

### ligne_echeance

Le détail par matière — indispensable pour justifier un montant à un parent qui conteste.

```sql
CREATE TABLE ligne_echeance (
    id           BIGSERIAL PRIMARY KEY,
    echeance_id  BIGINT NOT NULL REFERENCES echeance(id) ON DELETE CASCADE,
    matiere_id   BIGINT NOT NULL REFERENCES matiere(id),
    tarif_cents  BIGINT NOT NULL,
    CONSTRAINT ux_ligne_echeance UNIQUE (echeance_id, matiere_id)
);
```

### paiement

Écriture financière **immuable**. On n'édite jamais, on annule et on ressaisit.

```sql
CREATE TYPE mode_paiement AS ENUM ('ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE');
CREATE TYPE type_paiement AS ENUM ('MENSUALITE', 'INSCRIPTION');

CREATE TABLE paiement (
    id                 BIGSERIAL PRIMARY KEY,
    numero_recu        VARCHAR(20)   NOT NULL UNIQUE,   -- R-2025-000123
    eleve_id           BIGINT        NOT NULL REFERENCES eleve(id),
    type               type_paiement NOT NULL,
    periode            CHAR(7),                          -- NULL si type = INSCRIPTION
    montant_cents      BIGINT        NOT NULL,
    date_paiement      DATE          NOT NULL,
    mode               mode_paiement NOT NULL,
    observation        TEXT,
    -- annulation
    annule_le          TIMESTAMPTZ,
    annule_par         BIGINT        REFERENCES utilisateur(id),
    motif_annulation   TEXT,
    -- traçabilité
    cree_par           BIGINT        NOT NULL REFERENCES utilisateur(id),
    cree_le            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    cle_idempotence    UUID          UNIQUE,
    CONSTRAINT ck_paiement_positif CHECK (montant_cents > 0),
    CONSTRAINT ck_paiement_periode CHECK (
        (type = 'MENSUALITE' AND periode IS NOT NULL)
        OR (type = 'INSCRIPTION' AND periode IS NULL)
    ),
    CONSTRAINT ck_annulation CHECK (
        (annule_le IS NULL AND annule_par IS NULL AND motif_annulation IS NULL)
        OR (annule_le IS NOT NULL AND annule_par IS NOT NULL AND motif_annulation IS NOT NULL)
    )
);

CREATE INDEX ix_paiement_eleve   ON paiement (eleve_id, date_paiement DESC);
CREATE INDEX ix_paiement_periode ON paiement (periode) WHERE annule_le IS NULL;
CREATE INDEX ix_paiement_date    ON paiement (date_paiement) WHERE annule_le IS NULL;
```

> **La colonne `type` résout le double comptage** du §9. Les encaissements de type
> `MENSUALITE` et ceux de type `INSCRIPTION` sont deux ensembles disjoints, ce qui
> rend la formule du bénéfice net additive sans risque.

---

## 5. Professeurs et paie

```sql
CREATE TABLE professeur (
    id         BIGSERIAL PRIMARY KEY,
    nom        VARCHAR(80) NOT NULL,
    prenom     VARCHAR(80) NOT NULL,
    telephone  VARCHAR(20) NOT NULL,
    actif      BOOLEAN     NOT NULL DEFAULT TRUE,
    cree_le    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### affectation

Un professeur enseigne une matière sur un ou plusieurs niveaux (§5.2).

```sql
CREATE TABLE affectation (
    id                BIGSERIAL PRIMARY KEY,
    professeur_id     BIGINT     NOT NULL REFERENCES professeur(id),
    matiere_id        BIGINT     NOT NULL REFERENCES matiere(id),
    niveau_code       VARCHAR(5) NOT NULL REFERENCES niveau(code),
    annee_scolaire_id BIGINT     NOT NULL REFERENCES annee_scolaire(id),
    date_debut        DATE       NOT NULL,
    date_fin          DATE,
    cree_le           TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- ⚠ CONTRAINTE STRUCTURANTE — voir décision D3
    CONSTRAINT ux_affectation_unique
        UNIQUE (annee_scolaire_id, matiere_id, niveau_code)
);
```

> **Pourquoi cette unicité ?** La formule du §7.1 est
> `rémunération = tarif × nombre d'élèves du niveau inscrits à la matière`.
> Si deux professeurs partagent le couple (Maths, 2BAC), chacun est payé sur la
> **totalité** des élèves : le centre paie deux fois. La contrainte rend cette
> situation impossible en base plutôt que de la laisser produire une erreur de paie
> silencieuse. Le jour où le centre a réellement deux groupes, c'est la fonctionnalité
> « gestion des groupes » du §12 qui répond, pas un contournement.

### paie_mensuelle

```sql
CREATE TYPE statut_paie AS ENUM ('BROUILLON', 'VALIDEE', 'PAYEE');

CREATE TABLE paie_mensuelle (
    id             BIGSERIAL PRIMARY KEY,
    professeur_id  BIGINT      NOT NULL REFERENCES professeur(id),
    periode        CHAR(7)     NOT NULL,
    total_cents    BIGINT      NOT NULL DEFAULT 0,
    statut         statut_paie NOT NULL DEFAULT 'BROUILLON',
    genere_le      TIMESTAMPTZ NOT NULL DEFAULT now(),
    validee_le     TIMESTAMPTZ,
    validee_par    BIGINT      REFERENCES utilisateur(id),
    payee_le       DATE,
    mode_paiement  mode_paiement,
    CONSTRAINT ux_paie UNIQUE (professeur_id, periode),
    CONSTRAINT ck_paie_total CHECK (total_cents >= 0)
);
```

### ligne_paie

```sql
CREATE TABLE ligne_paie (
    id                    BIGSERIAL PRIMARY KEY,
    paie_id               BIGINT     NOT NULL REFERENCES paie_mensuelle(id) ON DELETE CASCADE,
    matiere_id            BIGINT     NOT NULL REFERENCES matiere(id),
    niveau_code           VARCHAR(5) NOT NULL REFERENCES niveau(code),
    nombre_eleves         INTEGER    NOT NULL,
    tarif_unitaire_cents  BIGINT     NOT NULL,   -- ⚠ FIGÉ à la génération
    montant_cents         BIGINT     NOT NULL,
    est_ajustement        BOOLEAN    NOT NULL DEFAULT FALSE,
    motif_ajustement      TEXT,
    CONSTRAINT ux_ligne_paie UNIQUE (paie_id, matiere_id, niveau_code, est_ajustement),
    CONSTRAINT ck_ligne_paie_calcul CHECK (
        est_ajustement OR montant_cents = nombre_eleves * tarif_unitaire_cents
    )
);
```

> La contrainte `ck_ligne_paie_calcul` fait vérifier l'arithmétique **par la base de
> données**. Aucun bug applicatif ne peut écrire une ligne de paie incohérente.
> Les lignes d'ajustement (régularisation d'un mois antérieur) en sont exemptées.

---

## 6. Charges du centre

```sql
CREATE TABLE categorie_charge (
    id      BIGSERIAL PRIMARY KEY,
    libelle VARCHAR(80) NOT NULL UNIQUE,
    actif   BOOLEAN     NOT NULL DEFAULT TRUE
);
-- Loyer, Électricité, Eau, Internet, Salaires administratifs,
-- Fournitures, Entretien, Publicité, Autres

CREATE TABLE charge (
    id                 BIGSERIAL PRIMARY KEY,
    categorie_id       BIGINT        NOT NULL REFERENCES categorie_charge(id),
    description        TEXT          NOT NULL,
    montant_cents      BIGINT        NOT NULL,
    date_charge        DATE          NOT NULL,
    periode            CHAR(7)       NOT NULL,   -- mois d'imputation comptable
    mode_paiement      mode_paiement NOT NULL,
    justificatif_chemin TEXT,                    -- chemin relatif, pas le binaire
    justificatif_type  VARCHAR(20),              -- image/jpeg, application/pdf
    cree_par           BIGINT        NOT NULL REFERENCES utilisateur(id),
    cree_le            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    annule_le          TIMESTAMPTZ,
    CONSTRAINT ck_charge_positive CHECK (montant_cents > 0),
    CONSTRAINT ck_charge_periode CHECK (periode ~ '^\d{4}-(0[1-9]|1[0-2])$')
);

CREATE INDEX ix_charge_periode ON charge (periode) WHERE annule_le IS NULL;
```

> `date_charge` et `periode` sont distincts volontairement : une facture d'électricité
> payée le 5 novembre peut concerner le mois d'octobre. Le dashboard raisonne sur
> `periode`, la trésorerie sur `date_charge`.
>
> Le justificatif est un **chemin**, jamais un `BYTEA`. Stocker des images en base
> gonfle les sauvegardes et ralentit tout.

---

## 7. Audit

```sql
CREATE TABLE journal_audit (
    id             BIGSERIAL PRIMARY KEY,
    utilisateur_id BIGINT      REFERENCES utilisateur(id),
    action         VARCHAR(30) NOT NULL,   -- CREATION, MODIFICATION, ANNULATION, VALIDATION, CONNEXION
    entite         VARCHAR(40) NOT NULL,
    entite_id      BIGINT,
    avant          JSONB,
    apres          JSONB,
    adresse_ip     INET,
    horodatage     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_audit_entite ON journal_audit (entite, entite_id, horodatage DESC);
CREATE INDEX ix_audit_date   ON journal_audit (horodatage DESC);

-- Ajout seul : le rôle applicatif ne peut ni modifier ni supprimer
REVOKE UPDATE, DELETE ON journal_audit FROM gep_app;
```

---

## 8. Règles de calcul

### 8.1 Montant dû mensuel d'un élève

```
montant_du(élève, période) = Σ inscription_matiere.tarif_mensuel_cents
  pour toutes les inscriptions actives durant la période
  et si eleve.statut = 'ACTIF'
```

Une inscription est active sur la période si `date_debut <= dernier jour du mois`
et (`date_fin IS NULL` OU `date_fin >= premier jour du mois`).

Un élève `SUSPENDU` ou `ARCHIVE` ne génère pas d'échéance.

> **Réduction** (D11, voir `docs/adr/2026-08-29-pack-et-reduction.md`). Si
> `eleve.reduction_mensuelle_cents` n'est pas NULL, `montant_du` n'est **pas**
> la somme ci-dessus : c'est ce montant fixe, saisi une fois et inchangé
> toute l'année. Les `inscription_matiere` existent quand même normalement —
> seul le montant facturé à l'élève change, jamais le comptage utilisé pour
> la paie professeur (§8.3, inchangée).
>
> **Pack** (D10, même ADR) n'a besoin d'aucune règle spéciale ici : le pack
> désigne littéralement toutes les matières tarifées du niveau, chacune
> inscrite avec le tarif du forfait fractionné (`eleve.est_pack = TRUE`).
> La somme ci-dessus s'applique sans modification et retombe exactement sur
> le forfait.

### 8.2 Statut d'une échéance

```
payé   = 0                     → NON_PAYE
0 < payé < dû                  → PARTIEL
payé >= dû                     → PAYE
```

Le cas `payé > dû` (trop-perçu) est autorisé et signalé sur la fiche élève. Il faut
un avoir pour le régulariser, pas une modification du montant dû.

### 8.3 Rémunération d'un professeur (§7)

```
Pour chaque affectation (matière M, niveau N) du professeur :
    nb_eleves = COUNT(élèves)
        WHERE eleve.niveau_code = N
          AND eleve.statut = 'ACTIF'
          AND eleve.annee_scolaire_id = année courante
          AND EXISTS une inscription_matiere active sur M pendant la période

    tarif      = tarif_professeur(année, N, M).montant_par_eleve_cents
    montant    = nb_eleves × tarif

Total paie = Σ des montants + Σ des lignes d'ajustement
```

Le tarif est lu **une fois**, à la génération, puis copié dans `ligne_paie`. Une
modification ultérieure du référentiel n'a aucun effet sur les paies déjà générées.

Régénérer une paie en statut `BROUILLON` écrase les lignes. Une paie `VALIDEE` ou
`PAYEE` est verrouillée : toute correction passe par une ligne d'ajustement.

### 8.4 Indicateurs du dashboard (§9)

Tous filtrés sur une période `YYYY-MM`, en ignorant les écritures annulées.

```
encaissements_mensualites = Σ paiement.montant_cents
    WHERE type='MENSUALITE' AND periode = P AND annule_le IS NULL

encaissements_inscriptions = Σ paiement.montant_cents
    WHERE type='INSCRIPTION'
      AND date_paiement dans le mois P
      AND annule_le IS NULL

total_charges = Σ charge.montant_cents WHERE periode = P AND annule_le IS NULL

total_paie = Σ paie_mensuelle.total_cents WHERE periode = P AND statut <> 'BROUILLON'

impayes = Σ (echeance.montant_du_cents - echeance.montant_paye_cents)
    WHERE periode = P AND statut <> 'PAYE'

BENEFICE_NET = encaissements_mensualites
             + encaissements_inscriptions
             - total_charges
             - total_paie

total_loyer = Σ charge.montant_cents
    WHERE periode = P AND annule_le IS NULL
      AND categorie_charge.libelle = 'Loyer'

FRAIS_INSCRIPTION_CUMULES =
    si CAISSIER : encaissements_inscriptions
    si ADMIN    : encaissements_inscriptions - (total_charges - total_loyer)
```

`FRAIS_INSCRIPTION_CUMULES` se calcule **différemment selon le rôle**, ce qui
est inhabituel dans ce modèle mais nécessaire ici : le calcul ADMIN retranche
les charges hors loyer, une information que le CAISSIER n'a jamais le droit
de voir (§6.6) — impossible de lui montrer la version nette sans exposer
indirectement les charges. Voir
`docs/adr/2026-08-16-marge-hors-loyer.md` (réécrit) pour le contexte. Le
loyer continue de compter normalement dans `total_charges` et
`BENEFICE_NET` ci-dessus — cette formule ne les affecte pas.

> **Correction apportée au §9.** La formule du cahier des charges additionne
> « encaissements totaux » et « total des frais d'inscription ». Si les frais
> d'inscription sont des encaissements, ils sont comptés deux fois. La colonne
> `paiement.type` rend les deux ensembles disjoints et la formule redevient exacte.
>
> La ligne « Montant des frais d'inscription cumulées = Somme des frais – les charges
> mensuelles » du §9 est en partie reprise ci-dessus, pour ADMIN seulement, avec le
> loyer explicitement exclu des charges retranchées — voir l'ADR pour la justification.

`total_paie` exclut les paies en `BROUILLON` : une paie non validée n'est pas un
engagement du centre et ne doit pas dégrader le bénéfice affiché.

---

## 9. Génération mensuelle

Deux tâches, planifiées et déclenchables manuellement.

**Génération des échéances** — le 1er de chaque mois. Pour chaque élève `ACTIF` de
l'année en cours, crée une `echeance` et ses `ligne_echeance` à partir des inscriptions
actives. Idempotente : relancer deux fois ne crée pas de doublon (`UNIQUE (eleve_id, periode)`).

**Génération de la paie** — le 1er du mois suivant, sur le mois écoulé. Crée une
`paie_mensuelle` en `BROUILLON` par professeur actif, avec ses lignes. L'administrateur
relit puis valide. Ne touche jamais une paie déjà validée.

Les deux écrivent un rapport d'exécution dans `journal_audit`.

---

## 10. Schéma relationnel

```
annee_scolaire ─┬─→ tarif_eleve ──────┐
                ├─→ tarif_professeur  │  (référentiel, copié à l'engagement)
                ├─→ eleve             │
                └─→ affectation       │
                                      │
niveau ─────────┬─→ eleve             │
                ├─→ tarif_*  ─────────┘
                ├─→ affectation
                └─→ ligne_paie

matiere ────────┬─→ tarif_*
                ├─→ inscription_matiere
                ├─→ affectation
                ├─→ ligne_echeance
                └─→ ligne_paie

eleve ──────────┬─→ inscription_matiere ──→ (tarif figé)
                ├─→ frais_inscription (1:1)
                ├─→ echeance ──→ ligne_echeance
                └─→ paiement

professeur ─────┬─→ affectation
                ├─→ paie_mensuelle ──→ ligne_paie ──→ (tarif figé)
                └─→ utilisateur (0:1)

categorie_charge ──→ charge

utilisateur ────→ journal_audit
```
