"""Expand password hash length

Revision ID: 9d3f7d4f2b18
Revises: a524776a1ebb
Create Date: 2026-06-08 20:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d3f7d4f2b18'
down_revision = 'a524776a1ebb'
branch_labels = None
depends_on = None


def upgrade():
    """Expand password hash column for modern Werkzeug hashes."""
    op.alter_column(
        'user',
        'password_hash',
        existing_type=sa.String(length=128),
        type_=sa.String(length=256),
        existing_nullable=True,
    )


def downgrade():
    """Restore the previous password hash column length."""
    op.alter_column(
        'user',
        'password_hash',
        existing_type=sa.String(length=256),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
