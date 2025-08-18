#!/usr/bin/env python3
"""
Database Migration Script for Sales Dashboard
Adds company column to existing tables and migrates data
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Migrate existing database to add company columns"""
    
    # Get database path
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, "instance", "sales_dashboard.db")
    
    if not os.path.exists(db_path):
        print("No existing database found. New database will be created with company support.")
        return True
    
    print(f"Migrating database at: {db_path}")
    
    # Create backup
    backup_path = db_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Database backup created: {backup_path}")
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if company column exists in advisors table
        cursor.execute("PRAGMA table_info(advisors)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations_needed = []
        
        if 'company' not in columns:
            migrations_needed.append('advisors')
        
        # Check teams table
        cursor.execute("PRAGMA table_info(teams)")
        teams_columns = [row[1] for row in cursor.fetchall()]
        if 'company' not in teams_columns:
            migrations_needed.append('teams')
        
        # Check submissions table
        cursor.execute("PRAGMA table_info(submissions)")
        submissions_columns = [row[1] for row in cursor.fetchall()]
        if 'company' not in submissions_columns:
            migrations_needed.append('submissions')
        
        # Check paid_cases table
        cursor.execute("PRAGMA table_info(paid_cases)")
        paid_cases_columns = [row[1] for row in cursor.fetchall()]
        if 'company' not in paid_cases_columns:
            migrations_needed.append('paid_cases')
        
        # Check sync_logs table
        cursor.execute("PRAGMA table_info(sync_logs)")
        sync_logs_columns = [row[1] for row in cursor.fetchall()]
        if 'company' not in sync_logs_columns:
            migrations_needed.append('sync_logs')
        
        if not migrations_needed:
            print("Database is already up to date!")
            return True
        
        print(f"Tables needing migration: {migrations_needed}")
        
        # Perform migrations
        if 'advisors' in migrations_needed:
            print("Adding company column to advisors table...")
            cursor.execute("ALTER TABLE advisors ADD COLUMN company VARCHAR(50) DEFAULT 'windsor'")
            cursor.execute("UPDATE advisors SET company = 'windsor' WHERE company IS NULL")
        
        if 'teams' in migrations_needed:
            print("Adding company column to teams table...")
            cursor.execute("ALTER TABLE teams ADD COLUMN company VARCHAR(50) DEFAULT 'windsor'")
            cursor.execute("UPDATE teams SET company = 'windsor' WHERE company IS NULL")
        
        if 'submissions' in migrations_needed:
            print("Adding company column to submissions table...")
            cursor.execute("ALTER TABLE submissions ADD COLUMN company VARCHAR(50) DEFAULT 'windsor'")
            cursor.execute("UPDATE submissions SET company = 'windsor' WHERE company IS NULL")
        
        if 'paid_cases' in migrations_needed:
            print("Adding company column to paid_cases table...")
            cursor.execute("ALTER TABLE paid_cases ADD COLUMN company VARCHAR(50) DEFAULT 'windsor'")
            cursor.execute("UPDATE paid_cases SET company = 'windsor' WHERE company IS NULL")
        
        if 'sync_logs' in migrations_needed:
            print("Adding company column to sync_logs table...")
            cursor.execute("ALTER TABLE sync_logs ADD COLUMN company VARCHAR(50) DEFAULT 'windsor'")
            cursor.execute("UPDATE sync_logs SET company = 'windsor' WHERE company IS NULL")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify migration
        cursor.execute("PRAGMA table_info(advisors)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"Advisors table columns after migration: {new_columns}")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n✅ Database migration completed successfully!")
        print("You can now run your application with: python app.py")
    else:
        print("\n❌ Database migration failed!")
        print("Please check the error messages above.")
