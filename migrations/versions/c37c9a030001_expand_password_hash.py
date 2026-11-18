"""Allow modern Werkzeug password hashes.

Revision ID: c37c9a030001
Revises: a524776a1ebb
"""
from alembic import op
import sqlalchemy as sa

revision = 'c37c9a030001'
down_revision = 'a524776a1ebb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(128),
                              type_=sa.String(256), existing_nullable=True)


def downgrade():
    # Keep the wider column to avoid truncating existing password hashes.
    pass
