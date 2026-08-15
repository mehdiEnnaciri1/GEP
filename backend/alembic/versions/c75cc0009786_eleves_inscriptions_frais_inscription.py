"""eleves : eleve, inscription_matiere, frais_inscription

Revision ID: c75cc0009786
Revises: 3e3db18e3679
Create Date: 2026-08-15 00:00:00.000000

Écrite à la main (Docker indisponible sur ce poste au moment de l'étape 3,
pas de base pour l'autogenerate) — à repasser par `alembic check` /
upgrade-downgrade-upgrade dès que Docker répond, avant de la considérer
définitive.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c75cc0009786'
down_revision: Union[str, Sequence[str], None] = '3e3db18e3679'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'eleve',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('matricule', sa.String(length=20), nullable=False),
        sa.Column('nom', sa.String(length=80), nullable=False),
        sa.Column('prenom', sa.String(length=80), nullable=False),
        sa.Column('telephone_eleve', sa.String(length=20), nullable=True),
        sa.Column('telephone_parent', sa.String(length=20), nullable=False),
        sa.Column('niveau_code', sa.String(length=5), nullable=False),
        sa.Column('annee_scolaire_id', sa.BigInteger(), nullable=False),
        sa.Column('date_inscription', sa.Date(), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('ACTIF', 'SUSPENDU', 'ARCHIVE', name='statut_eleve'),
            nullable=False,
        ),
        sa.Column('observation', sa.Text(), nullable=True),
        sa.Column('cree_par', sa.BigInteger(), nullable=False),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('modifie_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['annee_scolaire_id'], ['annee_scolaire.id']),
        sa.ForeignKeyConstraint(['cree_par'], ['utilisateur.id']),
        sa.ForeignKeyConstraint(['niveau_code'], ['niveau.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matricule'),
    )
    op.create_index(
        'ix_eleve_niveau_annee',
        'eleve',
        ['annee_scolaire_id', 'niveau_code'],
        unique=False,
        postgresql_where=sa.text("statut = 'ACTIF'"),
    )
    op.create_index('ix_eleve_nom', 'eleve', ['nom', 'prenom'], unique=False)

    op.create_table(
        'inscription_matiere',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('eleve_id', sa.BigInteger(), nullable=False),
        sa.Column('matiere_id', sa.BigInteger(), nullable=False),
        sa.Column('tarif_mensuel_cents', sa.BigInteger(), nullable=False),
        sa.Column('date_debut', sa.Date(), nullable=False),
        sa.Column('date_fin', sa.Date(), nullable=True),
        sa.Column('cree_par', sa.BigInteger(), nullable=False),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('date_fin IS NULL OR date_fin >= date_debut', name='ck_insc_dates'),
        sa.CheckConstraint('tarif_mensuel_cents >= 0', name='ck_insc_tarif'),
        sa.ForeignKeyConstraint(['cree_par'], ['utilisateur.id']),
        sa.ForeignKeyConstraint(['eleve_id'], ['eleve.id']),
        sa.ForeignKeyConstraint(['matiere_id'], ['matiere.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ux_inscription_active',
        'inscription_matiere',
        ['eleve_id', 'matiere_id'],
        unique=True,
        postgresql_where=sa.text('date_fin IS NULL'),
    )

    op.create_table(
        'frais_inscription',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('eleve_id', sa.BigInteger(), nullable=False),
        sa.Column('montant_cents', sa.BigInteger(), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('NON_PAYE', 'PAYE', name='statut_frais'),
            nullable=False,
        ),
        sa.Column('date_paiement', sa.Date(), nullable=True),
        sa.Column('mode_paiement', sa.String(length=20), nullable=True),
        sa.Column('paiement_id', sa.BigInteger(), nullable=True),
        sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "(statut = 'PAYE' AND date_paiement IS NOT NULL AND paiement_id IS NOT NULL) "
            "OR (statut = 'NON_PAYE' AND date_paiement IS NULL)",
            name='ck_frais_coherent',
        ),
        sa.ForeignKeyConstraint(['eleve_id'], ['eleve.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('eleve_id'),
    )


def downgrade() -> None:
    op.drop_table('frais_inscription')
    op.drop_index('ux_inscription_active', table_name='inscription_matiere', postgresql_where=sa.text('date_fin IS NULL'))
    op.drop_table('inscription_matiere')
    op.drop_index('ix_eleve_nom', table_name='eleve')
    op.drop_index('ix_eleve_niveau_annee', table_name='eleve', postgresql_where=sa.text("statut = 'ACTIF'"))
    op.drop_table('eleve')
    sa.Enum(name='statut_frais').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='statut_eleve').drop(op.get_bind(), checkfirst=True)
