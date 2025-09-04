# migration_add_original_business_type_sqlite.py
"""
SQLite Database migration to add original_business_type column
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models import db
from sqlalchemy import text

def main():
    """Run the SQLite migration"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🔄 Starting SQLite migration: Adding original_business_type column...")
        
        try:
            with db.engine.connect() as connection:
                # Check if column already exists using SQLite syntax
                result = connection.execute(text("PRAGMA table_info(submissions)"))
                columns = result.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'original_business_type' in column_names:
                    print("✅ Column 'original_business_type' already exists")
                    return
                
                print("📊 Creating backup of submissions table...")
                
                # Create backup table
                connection.execute(text("""
                    CREATE TABLE submissions_backup AS 
                    SELECT * FROM submissions
                """))
                
                print("✅ Backup created successfully")
                
                # Add the new column
                connection.execute(text("""
                    ALTER TABLE submissions 
                    ADD COLUMN original_business_type VARCHAR(100)
                """))
                
                print("✅ Added 'original_business_type' column")
                
                # Populate existing records with original business type data
                update_result = connection.execute(text("""
                    UPDATE submissions 
                    SET original_business_type = CASE 
                        WHEN business_type = 'Referral' AND referral_to IS NOT NULL AND referral_to != ''
                        THEN referral_to || ' Referral'
                        WHEN business_type = 'Referral' 
                        THEN 'Referral'
                        ELSE business_type
                    END
                    WHERE original_business_type IS NULL
                """))
                
                print(f"✅ Updated {update_result.rowcount} records with original_business_type data")
                
                # Commit the transaction
                connection.commit()
                
                # Verify the migration
                verification = connection.execute(text("""
                    SELECT COUNT(*) as total,
                           COUNT(original_business_type) as populated
                    FROM submissions
                """)).fetchone()
                
                print(f"📈 Verification: {verification.populated}/{verification.total} records have original_business_type populated")
                
                print("🎉 SQLite migration completed successfully!")
                print("💡 Backup table 'submissions_backup' created for safety")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to restore from backup if it exists
            try:
                with db.engine.connect() as connection:
                    # Check if backup exists
                    backup_check = connection.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='submissions_backup'
                    """)).fetchone()
                    
                    if backup_check:
                        print("🔄 Attempting to restore from backup...")
                        connection.execute(text("DROP TABLE IF EXISTS submissions"))
                        connection.execute(text("ALTER TABLE submissions_backup RENAME TO submissions"))
                        connection.commit()
                        print("✅ Restored from backup successfully")
                    
            except Exception as restore_error:
                print(f"❌ Failed to restore from backup: {restore_error}")
            
            db.session.rollback()

if __name__ == '__main__':
    main()