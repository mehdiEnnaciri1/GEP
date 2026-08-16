"""revocation refresh tokens

Revision ID: ef17453e7037
Revises: e5b6ba742707
Create Date: 2026-08-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ef17453e7037'
down_revision: Union[str, Sequence[str], None] = 'e5b6ba742707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'utilisateur',
        sa.Column('tokens_invalides_avant', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('utilisateur', 'tokens_invalides_avant')
