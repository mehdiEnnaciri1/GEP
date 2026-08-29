"""mode facturation pack et personnalise

Revision ID: ff24aaaf4ce9
Revises: ef17453e7037
Create Date: 2026-08-29 05:26:02.683456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ff24aaaf4ce9'
down_revision: Union[str, Sequence[str], None] = 'ef17453e7037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tarif_pack',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('annee_scolaire_id', sa.BigInteger(), nullable=False),
        sa.Column('niveau_code', sa.String(length=5), nullable=False),
        sa.Column('montant_cents', sa.BigInteger(), nullable=False),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modifie_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('montant_cents >= 0', name='ck_tarif_pack_positif'),
        sa.ForeignKeyConstraint(['annee_scolaire_id'], ['annee_scolaire.id'], ),
        sa.ForeignKeyConstraint(['niveau_code'], ['niveau.code'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('annee_scolaire_id', 'niveau_code', name='ux_tarif_pack'),
    )

    # `op.add_column` (contrairement à `create_table`) ne crée pas le type
    # ENUM tout seul : il faut le créer explicitement d'abord, puis
    # `create_type=False` pour empêcher SQLAlchemy de retenter sa création
    # implicite (voir le même piège documenté pour `mode_paiement` dans
    # e5b6ba742707_categorie_charge_et_charge.py).
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


def downgrade() -> None:
    op.drop_constraint('ck_eleve_facturation_coherente', 'eleve', type_='check')
    op.drop_column('eleve', 'montant_mensuel_fixe_cents')
    op.drop_column('eleve', 'mode_facturation')
    sa.Enum(name='mode_facturation').drop(op.get_bind(), checkfirst=True)

    op.drop_table('tarif_pack')
