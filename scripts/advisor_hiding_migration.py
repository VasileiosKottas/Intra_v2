"""
Migration to add individual advisor hiding functionality
This adds a new field to track if an advisor is hidden from other team members
while still being visible to masters.
"""

from flask_migrate import Migrate
from app.models import db

def upgrade():
    """Add is_hidden_from_team column to advisors table"""
    # Add the new column
    with db.engine.connect() as connection:
        connection.execute(db.text("""
            ALTER TABLE advisors 
            ADD COLUMN is_hidden_from_team BOOLEAN DEFAULT FALSE
        """))
        
        # Update existing records to default to visible
        connection.execute(db.text("""
            UPDATE advisors 
            SET is_hidden_from_team = FALSE 
            WHERE is_hidden_from_team IS NULL
        """))
        
        connection.commit()

def downgrade():
    """Remove is_hidden_from_team column from advisors table"""
    with db.engine.connect() as connection:
        connection.execute(db.text("""
            ALTER TABLE advisors 
            DROP COLUMN is_hidden_from_team
        """))
        connection.commit()

# If you're not using Flask-Migrate, run this SQL directly:
"""
-- Add the column
ALTER TABLE advisors ADD COLUMN is_hidden_from_team BOOLEAN DEFAULT FALSE;

-- Set default values for existing records
UPDATE advisors SET is_hidden_from_team = FALSE WHERE is_hidden_from_team IS NULL;
"""