"""categorie_charge et charge

Revision ID: e5b6ba742707
Revises: fad18153044b
Create Date: 2026-08-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5b6ba742707'
down_revision: Union[str, Sequence[str], None] = 'fad18153044b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('categorie_charge',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('libelle', sa.String(length=80), nullable=False),
    sa.Column('actif', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('libelle'),
    )
    op.create_table('charge',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('categorie_id', sa.BigInteger(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('montant_cents', sa.BigInteger(), nullable=False),
    sa.Column('date_charge', sa.Date(), nullable=False),
    sa.Column('periode', sa.String(length=7), nullable=False),
    # create_type=False : le type mode_paiement existe déjà (migration paiements).
    sa.Column(
        'mode_paiement',
        postgresql.ENUM(
            'ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE',
            name='mode_paiement', create_type=False,
        ),
        nullable=False,
    ),
    sa.Column('justificatif_chemin', sa.Text(), nullable=True),
    sa.Column('justificatif_type', sa.String(length=20), nullable=True),
    sa.Column('cree_par', sa.BigInteger(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('annule_le', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('montant_cents > 0', name='ck_charge_positive'),
    sa.CheckConstraint("periode ~ '^\\d{4}-(0[1-9]|1[0-2])$'", name='ck_charge_periode'),
    sa.ForeignKeyConstraint(['categorie_id'], ['categorie_charge.id'], name='fk_charge_categorie'),
    sa.ForeignKeyConstraint(['cree_par'], ['utilisateur.id'], name='fk_charge_utilisateur'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_charge_periode', 'charge', ['periode'],
        postgresql_where=sa.text('annule_le IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_charge_periode', table_name='charge')
    op.drop_table('charge')
    op.drop_table('categorie_charge')
