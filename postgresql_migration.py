# migration_add_original_business_type_postgresql.py
"""
PostgreSQL Production migration to add original_business_type column
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models import db
from sqlalchemy import text
from datetime import datetime

def main():
    """Run the PostgreSQL production migration"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🔄 Starting PostgreSQL production migration: Adding original_business_type column...")
        print("⚠️  PRODUCTION ENVIRONMENT - Creating backup before proceeding...")
        
        try:
            with db.engine.connect() as connection:
                # Check if column already exists using PostgreSQL syntax
                result = connection.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='submissions' AND column_name='original_business_type'
                """))
                
                if result.fetchone():
                    print("✅ Column 'original_business_type' already exists")
                    return
                
                # Start transaction for safety
                trans = connection.begin()
                
                try:
                    print("📊 Creating backup table with timestamp...")
                    
                    # Create timestamped backup table
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_table_name = f"submissions_backup_{timestamp}"
                    
                    connection.execute(text(f"""
                        CREATE TABLE {backup_table_name} AS 
                        SELECT * FROM submissions
                    """))
                    
                    # Get row count for verification
                    count_result = connection.execute(text("SELECT COUNT(*) FROM submissions")).fetchone()
                    original_count = count_result[0]
                    
                    print(f"✅ Backup created: {backup_table_name} with {original_count} records")
                    
                    # Add the new column
                    connection.execute(text("""
                        ALTER TABLE submissions 
                        ADD COLUMN original_business_type VARCHAR(100)
                    """))
                    
                    print("✅ Added 'original_business_type' column")
                    
                    # Create index on new column for better performance
                    connection.execute(text("""
                        CREATE INDEX idx_submissions_original_business_type 
                        ON submissions(original_business_type)
                    """))
                    
                    print("✅ Created index on original_business_type column")
                    
                    # Populate existing records with original business type data
                    update_result = connection.execute(text("""
                        UPDATE submissions 
                        SET original_business_type = CASE 
                            WHEN business_type = 'Referral' AND referral_to IS NOT NULL AND referral_to != ''
                            THEN CONCAT(referral_to, ' Referral')
                            WHEN business_type = 'Referral' 
                            THEN 'Referral'
                            ELSE business_type
                        END
                        WHERE original_business_type IS NULL
                    """))
                    
                    print(f"✅ Updated {update_result.rowcount} records with original_business_type data")
                    
                    # Verify the migration
                    verification = connection.execute(text("""
                        SELECT COUNT(*) as total,
                               COUNT(original_business_type) as populated,
                               COUNT(CASE WHEN business_type = 'Referral' THEN 1 END) as referrals
                        FROM submissions
                    """)).fetchone()
                    
                    print(f"📈 Verification:")
                    print(f"   Total records: {verification.total}")
                    print(f"   Records with original_business_type: {verification.populated}")
                    print(f"   Referral records: {verification.referrals}")
                    
                    # Additional verification - check referral data quality
                    referral_check = connection.execute(text("""
                        SELECT original_business_type, COUNT(*) as count
                        FROM submissions 
                        WHERE business_type = 'Referral'
                        GROUP BY original_business_type
                        ORDER BY count DESC
                        LIMIT 10
                    """)).fetchall()
                    
                    print(f"📋 Top referral types found:")
                    for row in referral_check:
                        print(f"   '{row.original_business_type}': {row.count} records")
                    
                    # Commit the transaction
                    trans.commit()
                    
                    print("🎉 PostgreSQL migration completed successfully!")
                    print(f"💡 Backup table '{backup_table_name}' created for safety")
                    print("⚡ Index created on original_business_type for optimal performance")
                    
                    # Final integrity check
                    final_count = connection.execute(text("SELECT COUNT(*) FROM submissions")).fetchone()[0]
                    if final_count == original_count:
                        print(f"✅ Integrity check passed: {final_count} records maintained")
                    else:
                        print(f"⚠️  Warning: Record count changed from {original_count} to {final_count}")
                
                except Exception as e:
                    print(f"❌ Migration failed during execution: {e}")
                    print("🔄 Rolling back transaction...")
                    trans.rollback()
                    raise
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            
            print("\n🚨 ROLLBACK INSTRUCTIONS:")
            print("If you need to rollback this migration, run:")
            print(f"DROP TABLE IF EXISTS submissions;")
            print(f"ALTER TABLE {backup_table_name} RENAME TO submissions;")
            print("(Replace backup table name with the actual timestamp)")
            
            # Don't use db.session.rollback() as we're using connection transactions
            return False
        
        return True

def rollback_migration():
    """Helper function to rollback the migration if needed"""
    print("🔄 Rollback functionality...")
    print("Available backup tables:")
    
    app_instance = SalesDashboardApp()
    with app_instance.app.app_context():
        with db.engine.connect() as connection:
            backup_tables = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'submissions_backup_%'
                ORDER BY table_name DESC
            """)).fetchall()
            
            for table in backup_tables:
                print(f"  - {table.table_name}")
            
            if backup_tables:
                latest_backup = backup_tables[0].table_name
                print(f"\nTo rollback to latest backup ({latest_backup}):")
                print(f"1. DROP TABLE IF EXISTS submissions;")
                print(f"2. ALTER TABLE {latest_backup} RENAME TO submissions;")
                print(f"3. DROP INDEX IF EXISTS idx_submissions_original_business_type;")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback_migration()
    else:
        success = main()
        if success:
            print("\n✨ Migration completed successfully!")
        else:
            print("\n💥 Migration failed - check logs above")