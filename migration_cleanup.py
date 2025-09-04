# migration_cleanup.py
"""
Cleanup script to remove backup tables after successful migration
Use this ONLY after confirming the migration worked correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models import db
from sqlalchemy import text

def cleanup_sqlite_backups():
    """Clean up SQLite backup tables"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🧹 Cleaning up SQLite backup tables...")
        
        try:
            with db.engine.connect() as connection:
                # Find backup tables
                backup_tables = connection.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE '%backup%'
                """)).fetchall()
                
                if not backup_tables:
                    print("✅ No backup tables found to clean up")
                    return
                
                print(f"Found {len(backup_tables)} backup tables:")
                for table in backup_tables:
                    print(f"  - {table.name}")
                
                confirm = input("\n❓ Are you sure you want to delete these backup tables? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("❌ Cleanup cancelled")
                    return
                
                for table in backup_tables:
                    connection.execute(text(f"DROP TABLE {table.name}"))
                    print(f"🗑️  Dropped {table.name}")
                
                connection.commit()
                print("✅ SQLite cleanup completed")
                
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

def cleanup_postgresql_backups():
    """Clean up PostgreSQL backup tables"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("🧹 Cleaning up PostgreSQL backup tables...")
        
        try:
            with db.engine.connect() as connection:
                # Find backup tables
                backup_tables = connection.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name LIKE 'submissions_backup_%'
                    ORDER BY table_name
                """)).fetchall()
                
                if not backup_tables:
                    print("✅ No backup tables found to clean up")
                    return
                
                print(f"Found {len(backup_tables)} backup tables:")
                for table in backup_tables:
                    # Get table size info
                    size_result = connection.execute(text(f"""
                        SELECT COUNT(*) as row_count,
                               pg_size_pretty(pg_total_relation_size('{table.table_name}')) as size
                        FROM {table.table_name}
                    """)).fetchone()
                    print(f"  - {table.table_name} ({size_result.row_count} rows, {size_result.size})")
                
                print("\n⚠️  WARNING: This will permanently delete backup data!")
                confirm = input("❓ Are you sure you want to delete these backup tables? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("❌ Cleanup cancelled")
                    return
                
                for table in backup_tables:
                    connection.execute(text(f"DROP TABLE {table.table_name}"))
                    print(f"🗑️  Dropped {table.table_name}")
                
                connection.commit()
                print("✅ PostgreSQL cleanup completed")
                
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

def main():
    """Main cleanup function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migration_cleanup.py sqlite    - Clean SQLite backups")
        print("  python migration_cleanup.py postgres - Clean PostgreSQL backups")
        return
    
    db_type = sys.argv[1].lower()
    
    if db_type in ['sqlite', 'sqlite3']:
        cleanup_sqlite_backups()
    elif db_type in ['postgres', 'postgresql', 'pg']:
        cleanup_postgresql_backups()
    else:
        print(f"❌ Unknown database type: {db_type}")
        print("Use 'sqlite' or 'postgres'")

if __name__ == '__main__':
    main()