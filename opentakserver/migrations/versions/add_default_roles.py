"""Add default roles

Revision ID: add_default_roles
Revises: add_callsign_user
Create Date: 2025-11-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_default_roles'
down_revision = 'add_callsign_user'
branch_labels = None
depends_on = None


def upgrade():
    # Create a connection to execute raw SQL
    conn = op.get_bind()
    
    # Check if roles already exist before inserting
    # This prevents duplicate key errors on re-runs
    
    # Insert administrator role if it doesn't exist
    conn.execute(sa.text("""
        INSERT INTO role (name, description, permissions, update_datetime)
        SELECT 'administrator', 'Administrator role with full access', NULL, :timestamp
        WHERE NOT EXISTS (SELECT 1 FROM role WHERE name = 'administrator')
    """), {'timestamp': datetime.utcnow()})
    
    # Insert user role if it doesn't exist
    conn.execute(sa.text("""
        INSERT INTO role (name, description, permissions, update_datetime)
        SELECT 'user', 'Standard user role with basic permissions', NULL, :timestamp
        WHERE NOT EXISTS (SELECT 1 FROM role WHERE name = 'user')
    """), {'timestamp': datetime.utcnow()})
    
    # Insert player role if it doesn't exist
    conn.execute(sa.text("""
        INSERT INTO role (name, description, permissions, update_datetime)
        SELECT 'player', 'Player role for game participants', NULL, :timestamp
        WHERE NOT EXISTS (SELECT 1 FROM role WHERE name = 'player')
    """), {'timestamp': datetime.utcnow()})


def downgrade():
    # Remove the default roles
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role WHERE name IN ('administrator', 'user', 'player')"))
