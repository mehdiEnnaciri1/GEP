"""séquences Postgres pour matricule et numéro de reçu

Revision ID: 999830e822b1
Revises: 998d2219e3e3
Create Date: 2026-08-16 00:00:00.000000

Remplace le comptage puis + 1 (course possible entre deux saisies
simultanées : les deux comptent N lignes existantes avant que l'une des deux
insertions ne commite, et produisent le même numéro suivant) par une vraie
SEQUENCE Postgres — `nextval()` est atomique, deux appels concurrents
obtiennent toujours deux valeurs distinctes, garanti par Postgres lui-même,
pas par le code applicatif.

Conséquence assumée : la numérotation devient monotone globale (le préfixe
année de `E-{année}-NNNNNN` reste celui de la création réelle, mais le
compteur ne repart plus à 1 à chaque nouvelle année scolaire — un
comptage par année empêcherait justement l'usage d'une séquence simple).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '999830e822b1'
down_revision: Union[str, Sequence[str], None] = '998d2219e3e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE seq_matricule_eleve START WITH 1")
    op.execute("CREATE SEQUENCE seq_numero_recu_paiement START WITH 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE seq_numero_recu_paiement")
    op.execute("DROP SEQUENCE seq_matricule_eleve")
