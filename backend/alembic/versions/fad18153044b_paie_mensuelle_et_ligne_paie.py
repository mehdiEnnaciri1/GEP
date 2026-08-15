"""paie_mensuelle et ligne_paie

Revision ID: fad18153044b
Revises: 949a906ceff1
Create Date: 2026-08-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fad18153044b'
down_revision: Union[str, Sequence[str], None] = '949a906ceff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('paie_mensuelle',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('professeur_id', sa.BigInteger(), nullable=False),
    sa.Column('periode', sa.String(length=7), nullable=False),
    sa.Column('total_cents', sa.BigInteger(), nullable=False),
    sa.Column('statut', sa.Enum('BROUILLON', 'VALIDEE', 'PAYEE', name='statut_paie'), nullable=False),
    sa.Column('genere_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('validee_le', sa.DateTime(timezone=True), nullable=True),
    sa.Column('validee_par', sa.BigInteger(), nullable=True),
    sa.Column('payee_le', sa.Date(), nullable=True),
    # create_type=False : le type mode_paiement existe déjà (créé par la
    # migration paiements), le recréer ferait échouer avec "type already
    # exists" — ce flag n'est lu que par postgresql.ENUM, pas par sa.Enum
    # générique (qui l'ignore silencieusement et tenterait de le recréer).
    sa.Column(
        'mode_paiement',
        postgresql.ENUM(
            'ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE',
            name='mode_paiement', create_type=False,
        ),
        nullable=True,
    ),
    sa.CheckConstraint('total_cents >= 0', name='ck_paie_total'),
    sa.CheckConstraint("periode ~ '^\\d{4}-(0[1-9]|1[0-2])$'", name='ck_paie_periode_format'),
    sa.ForeignKeyConstraint(['professeur_id'], ['professeur.id'], name='fk_paie_professeur'),
    sa.ForeignKeyConstraint(['validee_par'], ['utilisateur.id'], name='fk_paie_validee_par'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('professeur_id', 'periode', name='ux_paie'),
    )
    op.create_table('ligne_paie',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('paie_id', sa.BigInteger(), nullable=False),
    sa.Column('matiere_id', sa.BigInteger(), nullable=False),
    sa.Column('niveau_code', sa.String(length=5), nullable=False),
    sa.Column('nombre_eleves', sa.Integer(), nullable=False),
    sa.Column('tarif_unitaire_cents', sa.BigInteger(), nullable=False),
    sa.Column('montant_cents', sa.BigInteger(), nullable=False),
    sa.Column('est_ajustement', sa.Boolean(), nullable=False),
    sa.Column('motif_ajustement', sa.Text(), nullable=True),
    sa.CheckConstraint(
        'est_ajustement OR montant_cents = nombre_eleves * tarif_unitaire_cents',
        name='ck_ligne_paie_calcul',
    ),
    sa.ForeignKeyConstraint(['paie_id'], ['paie_mensuelle.id'], name='fk_ligne_paie_paie', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['matiere_id'], ['matiere.id'], name='fk_ligne_paie_matiere'),
    sa.ForeignKeyConstraint(['niveau_code'], ['niveau.code'], name='fk_ligne_paie_niveau'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('paie_id', 'matiere_id', 'niveau_code', 'est_ajustement', name='ux_ligne_paie'),
    )


def downgrade() -> None:
    op.drop_table('ligne_paie')
    op.drop_table('paie_mensuelle')
    sa.Enum(name='statut_paie').drop(op.get_bind(), checkfirst=True)
