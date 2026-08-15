"""professeurs et affectations

Revision ID: 949a906ceff1
Revises: 999830e822b1
Create Date: 2026-08-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '949a906ceff1'
down_revision: Union[str, Sequence[str], None] = '999830e822b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('professeur',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('nom', sa.String(length=80), nullable=False),
    sa.Column('prenom', sa.String(length=80), nullable=False),
    sa.Column('telephone', sa.String(length=20), nullable=False),
    sa.Column('actif', sa.Boolean(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('affectation',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('professeur_id', sa.BigInteger(), nullable=False),
    sa.Column('matiere_id', sa.BigInteger(), nullable=False),
    sa.Column('niveau_code', sa.String(length=5), nullable=False),
    sa.Column('annee_scolaire_id', sa.BigInteger(), nullable=False),
    sa.Column('date_debut', sa.Date(), nullable=False),
    sa.Column('date_fin', sa.Date(), nullable=True),
    sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['professeur_id'], ['professeur.id'], name='fk_affectation_professeur'),
    sa.ForeignKeyConstraint(['matiere_id'], ['matiere.id'], name='fk_affectation_matiere'),
    sa.ForeignKeyConstraint(['niveau_code'], ['niveau.code'], name='fk_affectation_niveau'),
    sa.ForeignKeyConstraint(['annee_scolaire_id'], ['annee_scolaire.id'], name='fk_affectation_annee'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('annee_scolaire_id', 'matiere_id', 'niveau_code', name='ux_affectation_unique'),
    )
    # FK différée depuis l'étape 1 (utilisateur.professeur_id existait déjà,
    # nullable, sans contrainte, faute de table `professeur`) : elle peut
    # maintenant être posée.
    op.create_foreign_key(
        'fk_utilisateur_professeur', 'utilisateur', 'professeur', ['professeur_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_utilisateur_professeur', 'utilisateur', type_='foreignkey')
    op.drop_table('affectation')
    op.drop_table('professeur')
