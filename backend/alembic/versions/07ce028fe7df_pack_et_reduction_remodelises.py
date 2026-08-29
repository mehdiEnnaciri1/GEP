"""pack et reduction remodelises

Revision ID: 07ce028fe7df
Revises: ff24aaaf4ce9
Create Date: 2026-08-29 05:59:25.728079

Remplace `eleve.mode_facturation` (NORMAL/PACK/PERSONNALISE, montant unique)
par deux colonnes indépendantes — voir docs/adr/2026-08-29-pack-et-reduction.md
(réécrit) : le pack désigne littéralement les matières du niveau (tarif
fractionné sur chaque inscription réelle), la réduction est un montant fixe
qui n'affecte que l'échéance, jamais les inscriptions.

Migration de données incluse (pas seulement de schéma) : les élèves déjà
créés sous l'ancien modèle sont convertis, pas juste les colonnes ajoutées à
vide.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '07ce028fe7df'
down_revision: Union[str, Sequence[str], None] = 'ff24aaaf4ce9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables():
    eleve_t = sa.table(
        'eleve',
        sa.column('id', sa.BigInteger),
        sa.column('niveau_code', sa.String),
        sa.column('annee_scolaire_id', sa.BigInteger),
        sa.column(
            'mode_facturation',
            postgresql.ENUM(
                'NORMAL', 'PACK', 'PERSONNALISE', name='mode_facturation', create_type=False
            ),
        ),
        sa.column('montant_mensuel_fixe_cents', sa.BigInteger),
        sa.column('est_pack', sa.Boolean),
        sa.column('reduction_mensuelle_cents', sa.BigInteger),
    )
    inscription_t = sa.table(
        'inscription_matiere',
        sa.column('id', sa.BigInteger),
        sa.column('eleve_id', sa.BigInteger),
        sa.column('matiere_id', sa.BigInteger),
        sa.column('tarif_mensuel_cents', sa.BigInteger),
        sa.column('date_fin', sa.Date),
    )
    tarif_pack_t = sa.table(
        'tarif_pack',
        sa.column('annee_scolaire_id', sa.BigInteger),
        sa.column('niveau_code', sa.String),
        sa.column('montant_cents', sa.BigInteger),
    )
    return eleve_t, inscription_t, tarif_pack_t


def upgrade() -> None:
    op.add_column(
        'eleve',
        sa.Column('est_pack', sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        'eleve', sa.Column('reduction_mensuelle_cents', sa.BigInteger(), nullable=True)
    )
    op.create_check_constraint(
        'ck_eleve_reduction_positive',
        'eleve',
        'reduction_mensuelle_cents IS NULL OR reduction_mensuelle_cents >= 0',
    )
    op.create_check_constraint(
        'ck_eleve_pack_reduction_exclusifs',
        'eleve',
        'NOT (est_pack AND reduction_mensuelle_cents IS NOT NULL)',
    )

    bind = op.get_bind()
    eleve_t, inscription_t, tarif_pack_t = _tables()

    # PERSONNALISE -> reduction_mensuelle_cents (copie directe : les
    # inscriptions réelles de ces élèves correspondaient déjà à ce que le
    # nouveau modèle attend, rien à recalculer).
    bind.execute(
        eleve_t.update()
        .where(eleve_t.c.mode_facturation == 'PERSONNALISE')
        .values(reduction_mensuelle_cents=eleve_t.c.montant_mensuel_fixe_cents)
    )

    # PACK -> est_pack=TRUE, et chaque inscription active recalculée au tarif
    # pack fractionné (division entière, reste en centimes sur la première
    # matière pour que la somme retombe exactement sur le forfait).
    eleves_pack = bind.execute(
        sa.select(eleve_t.c.id, eleve_t.c.niveau_code, eleve_t.c.annee_scolaire_id).where(
            eleve_t.c.mode_facturation == 'PACK'
        )
    ).fetchall()

    for eleve_id, niveau_code, annee_scolaire_id in eleves_pack:
        bind.execute(eleve_t.update().where(eleve_t.c.id == eleve_id).values(est_pack=True))

        tarif_pack_cents = bind.execute(
            sa.select(tarif_pack_t.c.montant_cents).where(
                tarif_pack_t.c.annee_scolaire_id == annee_scolaire_id,
                tarif_pack_t.c.niveau_code == niveau_code,
            )
        ).scalar_one_or_none()
        if tarif_pack_cents is None:
            continue  # ne devrait pas arriver (vérifié à la création) — sécurité seulement

        lignes = bind.execute(
            sa.select(inscription_t.c.id)
            .where(inscription_t.c.eleve_id == eleve_id, inscription_t.c.date_fin.is_(None))
            .order_by(inscription_t.c.id)
        ).fetchall()
        nombre = len(lignes)
        if nombre == 0:
            continue
        part = tarif_pack_cents // nombre
        reste = tarif_pack_cents - part * nombre
        for index, (inscription_id,) in enumerate(lignes):
            montant = part + (reste if index == 0 else 0)
            bind.execute(
                inscription_t.update()
                .where(inscription_t.c.id == inscription_id)
                .values(tarif_mensuel_cents=montant)
            )

    op.drop_constraint('ck_eleve_facturation_coherente', 'eleve', type_='check')
    op.drop_column('eleve', 'montant_mensuel_fixe_cents')
    op.drop_column('eleve', 'mode_facturation')
    sa.Enum(name='mode_facturation').drop(bind, checkfirst=True)


def downgrade() -> None:
    mode_facturation = postgresql.ENUM(
        'NORMAL', 'PACK', 'PERSONNALISE', name='mode_facturation'
    )
    mode_facturation.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'eleve',
        sa.Column(
            'mode_facturation',
            postgresql.ENUM(
                'NORMAL', 'PACK', 'PERSONNALISE', name='mode_facturation', create_type=False
            ),
            server_default='NORMAL',
            nullable=False,
        ),
    )
    op.add_column(
        'eleve', sa.Column('montant_mensuel_fixe_cents', sa.BigInteger(), nullable=True)
    )
    op.create_check_constraint(
        'ck_eleve_facturation_coherente',
        'eleve',
        "(mode_facturation = 'NORMAL' AND montant_mensuel_fixe_cents IS NULL) "
        "OR (mode_facturation <> 'NORMAL' AND montant_mensuel_fixe_cents IS NOT NULL "
        "AND montant_mensuel_fixe_cents >= 0)",
    )

    # Reconversion best-effort : le fractionnement du tarif pack sur les
    # inscriptions n'est PAS défait (il faudrait relire tarif_eleve pour
    # restaurer les tarifs réels, hors de portée d'un downgrade de schéma).
    bind = op.get_bind()
    eleve_t, _, _ = _tables()
    bind.execute(eleve_t.update().where(eleve_t.c.est_pack.is_(True)).values(mode_facturation='PACK'))
    bind.execute(
        eleve_t.update()
        .where(eleve_t.c.reduction_mensuelle_cents.isnot(None))
        .values(
            mode_facturation='PERSONNALISE',
            montant_mensuel_fixe_cents=eleve_t.c.reduction_mensuelle_cents,
        )
    )

    op.drop_constraint('ck_eleve_pack_reduction_exclusifs', 'eleve', type_='check')
    op.drop_constraint('ck_eleve_reduction_positive', 'eleve', type_='check')
    op.drop_column('eleve', 'reduction_mensuelle_cents')
    op.drop_column('eleve', 'est_pack')
