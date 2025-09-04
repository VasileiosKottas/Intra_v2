# reset_and_resync_referrals.py
"""
Script to:
1. Remove original_business_type column
2. Clear existing referral data
3. Re-sync all data from JotForm with corrected processing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models import db
from app.services.sync import DataSyncService
from sqlalchemy import text
from datetime import datetime

def reset_and_resync():
    """Reset database and re-sync with corrected referral processing"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🔄 RESET AND RE-SYNC PROCESS STARTING...")
        print("This will:")
        print("1. Remove original_business_type column")
        print("2. Clear existing referral submissions")
        print("3. Re-sync ALL data from JotForm with corrected processing")
        
        confirm = input("\n❓ Are you sure you want to proceed? This will modify your database. (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Operation cancelled")
            return
        
        try:
            with db.engine.connect() as connection:
                # Start transaction
                trans = connection.begin()
                
                try:
                    print("\n📋 Step 1: Creating backup of current submissions...")
                    
                    # Create backup table with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_table = f"submissions_backup_before_reset_{timestamp}"
                    
                    connection.execute(text(f"""
                        CREATE TABLE {backup_table} AS 
                        SELECT * FROM submissions
                    """))
                    
                    backup_count = connection.execute(text(f"SELECT COUNT(*) FROM {backup_table}")).fetchone()[0]
                    print(f"✅ Backup created: {backup_table} with {backup_count} records")
                    
                    print("\n🗑️  Step 2: Removing original_business_type column...")
                    
                    # SQLite doesn't support DROP COLUMN directly, so we recreate the table
                    connection.execute(text("""
                        CREATE TABLE submissions_new AS
                        SELECT 
                            advisor_name,
                            advisor_id,
                            business_type,
                            submission_date,
                            customer_name,
                            expected_proc,
                            expected_fee,
                            referral_to,
                            company,
                            jotform_id,
                            id,
                            created_at
                        FROM submissions
                    """))
                    
                    # Drop old table and rename new one
                    connection.execute(text("DROP TABLE submissions"))
                    connection.execute(text("ALTER TABLE submissions_new RENAME TO submissions"))
                    
                    print("✅ original_business_type column removed")
                    
                    print("\n🧹 Step 3: Clearing existing referral submissions...")
                    
                    # Get count before deletion
                    referral_count = connection.execute(text("""
                        SELECT COUNT(*) FROM submissions 
                        WHERE LOWER(business_type) LIKE '%referral%'
                    """)).fetchone()[0]
                    
                    print(f"Found {referral_count} existing referral submissions")
                    
                    # Delete existing referrals
                    connection.execute(text("""
                        DELETE FROM submissions 
                        WHERE LOWER(business_type) LIKE '%referral%'
                    """))
                    
                    remaining_count = connection.execute(text("SELECT COUNT(*) FROM submissions")).fetchone()[0]
                    print(f"✅ Removed {referral_count} referral submissions, {remaining_count} non-referral submissions remain")
                    
                    # Commit the cleanup
                    trans.commit()
                    print("✅ Database reset completed successfully")
                    
                except Exception as e:
                    print(f"❌ Database reset failed: {e}")
                    trans.rollback()
                    return False
            
            print(f"\n🔄 Step 4: Re-syncing ALL data from JotForm...")
            print("This will use the corrected processing logic to capture Survey/Conveyancing referrals")
            
            # Re-sync both companies
            companies = ['windsor', 'cnc']
            total_new_submissions = 0
            total_new_paid_cases = 0
            
            for company in companies:
                print(f"\n📄 Re-syncing {company.upper()}...")
                
                sync_service = DataSyncService(company)
                submissions_added, paid_cases_added, success, error = sync_service.perform_sync()
                
                if success:
                    print(f"✅ {company.upper()} sync completed!")
                    print(f"   📄 New submissions: {submissions_added}")
                    print(f"   💰 New paid cases: {paid_cases_added}")
                    total_new_submissions += submissions_added
                    total_new_paid_cases += paid_cases_added
                else:
                    print(f"❌ {company.upper()} sync failed: {error}")
            
            print(f"\n🎉 RESET AND RE-SYNC COMPLETED!")
            print(f"Summary:")
            print(f"  📄 Total new submissions: {total_new_submissions}")
            print(f"  💰 Total new paid cases: {total_new_paid_cases}")
            print(f"  🗄️  Backup table: {backup_table}")
            
            # Final verification
            with db.engine.connect() as connection:
                final_stats = connection.execute(text("""
                    SELECT 
                        COUNT(*) as total_submissions,
                        COUNT(CASE WHEN LOWER(business_type) LIKE '%referral%' THEN 1 END) as referral_submissions
                    FROM submissions
                """)).fetchone()
                
                print(f"\n📊 Final database stats:")
                print(f"  Total submissions: {final_stats.total_submissions}")
                print(f"  Referral submissions: {final_stats.referral_submissions}")
                
                # Show referral breakdown
                if final_stats.referral_submissions > 0:
                    referral_breakdown = connection.execute(text("""
                        SELECT business_type, COUNT(*) as count
                        FROM submissions 
                        WHERE LOWER(business_type) LIKE '%referral%'
                        GROUP BY business_type
                        ORDER BY count DESC
                    """)).fetchall()
                    
                    print(f"\n📋 Referral types captured:")
                    for row in referral_breakdown:
                        print(f"  '{row.business_type}': {row.count} records")
            
            print(f"\n💡 Next steps:")
            print(f"1. Run your analysis script to verify Survey/Conveyancing referrals are now captured")
            print(f"2. Test your YTD dashboard to ensure proper categorization")
            print(f"3. If satisfied, you can clean up the backup table: DROP TABLE {backup_table}")
            
            return True
            
        except Exception as e:
            print(f"❌ Reset and re-sync failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def rollback_reset():
    """Rollback function in case something goes wrong"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🔄 ROLLBACK PROCESS")
        
        try:
            with db.engine.connect() as connection:
                # Find backup tables
                backup_tables = connection.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE 'submissions_backup_before_reset_%'
                    ORDER BY name DESC
                """)).fetchall()
                
                if not backup_tables:
                    print("❌ No backup tables found")
                    return
                
                print("Available backup tables:")
                for i, table in enumerate(backup_tables):
                    print(f"  {i+1}. {table.name}")
                
                choice = input("Enter the number of the backup to restore (or 'cancel'): ")
                if choice.lower() == 'cancel':
                    print("❌ Rollback cancelled")
                    return
                
                try:
                    backup_index = int(choice) - 1
                    selected_backup = backup_tables[backup_index].name
                except (ValueError, IndexError):
                    print("❌ Invalid selection")
                    return
                
                print(f"🔄 Restoring from {selected_backup}...")
                
                # Restore from backup
                connection.execute(text("DROP TABLE IF EXISTS submissions"))
                connection.execute(text(f"ALTER TABLE {selected_backup} RENAME TO submissions"))
                
                final_count = connection.execute(text("SELECT COUNT(*) FROM submissions")).fetchone()[0]
                print(f"✅ Restored {final_count} records from backup")
                
        except Exception as e:
            print(f"❌ Rollback failed: {e}")

def main():
    """Main function with options"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'rollback':
            rollback_reset()
            return
    
    success = reset_and_resync()
    if not success:
        print("\n💥 Process failed. To rollback, run:")
        print("python reset_and_resync_referrals.py rollback")

if __name__ == '__main__':
    main()