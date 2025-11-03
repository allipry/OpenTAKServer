"""Add callsign column to user table

Revision ID: add_callsign_user
Revises: d68964dab66b
Create Date: 2025-11-03 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_callsign_user'
down_revision = 'd68964dab66b'
branch_labels = None
depends_on = None


def upgrade():
    # Add callsign column to user table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    if 'callsign' not in columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('callsign', sa.String(length=255), nullable=True))


def downgrade():
    # Remove callsign column from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('callsign')
