"""Create the followers table omitted from the original migrations.

Revision ID: c37c9a030002
Revises: 9d3f7d4f2b18
"""
from alembic import op
import sqlalchemy as sa

revision = 'c37c9a030002'
down_revision = '9d3f7d4f2b18'
branch_labels = None
depends_on = None


def upgrade():
    # Some development databases already have this table from db.create_all().
    # Keep any existing relationships instead of replacing their table.
    if not sa.inspect(op.get_bind()).has_table('followers'):
        op.create_table(
            'followers',
            sa.Column('follower_id', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('followed_id', sa.Integer(), sa.ForeignKey('user.id')),
        )


def downgrade():
    op.drop_table('followers')
