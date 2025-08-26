#!/usr/bin/env python3
"""
Database Migration Script for Adding income_type Column - LOCALHOST VERSION (PAID CASES ONLY)
Run this locally to update your SQLite database schema
"""

import os
import sys
import sqlite3
from pathlib import Path

def get_database_path():
    """Get the SQLite database path for localhost"""
    # Look for the database in the instance folder
    instance_path = Path(__file__).parent / "instance" / "sales_dashboard.db"
    
    if instance_path.exists():
        return str(instance_path)
    
    # Alternative paths to check
    alt_paths = [
        Path(__file__).parent / "sales_dashboard.db",
        Path(__file__).parent / "app" / "sales_dashboard.db",
        Path(__file__).parent / "data" / "sales_dashboard.db"
    ]
    
    for path in alt_paths:
        if path.exists():
            return str(path)
    
    # If not found, use the default instance path
    instance_path.parent.mkdir(parents=True, exist_ok=True)
    return str(instance_path)

def run_sqlite_migration():
    """Run the database migration for SQLite (localhost) - PAID CASES ONLY"""
    
    db_path = get_database_path()
    print(f"Database path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Warning: Database file not found at {db_path}")
        print("The migration will create the columns when you first run the app")
        return
    
    try:
        print("Starting SQLite database migration...")
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists in paid_cases table
        print("Checking existing schema...")
        
        cursor.execute("PRAGMA table_info(paid_cases)")
        paid_cases_columns = [row[1] for row in cursor.fetchall()]
        paid_cases_has_income_type = 'income_type' in paid_cases_columns
        
        print(f"Paid_cases table has income_type: {paid_cases_has_income_type}")
        
        # Add income_type to paid_cases table if not exists
        if not paid_cases_has_income_type:
            print("Adding income_type column to paid_cases table...")
            cursor.execute("""
                ALTER TABLE paid_cases 
                ADD COLUMN income_type TEXT;
            """)
            print("Added income_type column to paid_cases table")
        else:
            print("income_type column already exists in paid_cases table")
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the changes
        print("\nVerifying migration...")
        
        # Check paid_cases table structure  
        cursor.execute("PRAGMA table_info(paid_cases)")
        paid_cases_info = cursor.fetchall()
        
        print("Paid_cases table columns:")
        for column_info in paid_cases_info:
            column_name = column_info[1]
            column_type = column_info[2]
            is_nullable = "YES" if column_info[3] == 0 else "NO"
            if column_name in ['income_type', 'case_type', 'who_referred']:
                print(f"  - {column_name}: {column_type} (nullable: {is_nullable})")
                
        # Close connection
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

def run_flask_migration():
    """Alternative: Run migration using Flask app context (if SQLite direct access fails)"""
    try:
        print("Running migration using Flask app context...")
        
        from app import create_app
        from app.models import db
        from sqlalchemy import text
        
        # Create app and context
        app = create_app('development')
        
        with app.app_context():
            # Check if column already exists
            print("Checking existing schema...")
            
            try:
                db.engine.execute(text("SELECT income_type FROM paid_cases LIMIT 1"))
                paid_cases_has_income_type = True
            except:
                paid_cases_has_income_type = False
            
            print(f"Paid_cases table has income_type: {paid_cases_has_income_type}")
            
            # Add income_type to paid_cases table if not exists
            if not paid_cases_has_income_type:
                print("Adding income_type column to paid_cases table...")
                db.engine.execute(text("""
                    ALTER TABLE paid_cases 
                    ADD COLUMN income_type TEXT;
                """))
                print("Added income_type column to paid_cases table")
            
            # Commit the changes
            db.session.commit()
            print("Flask migration completed successfully!")
            
    except Exception as e:
        print(f"Flask migration failed: {str(e)}")
        print("Trying direct SQLite approach instead...")
        run_sqlite_migration()

if __name__ == "__main__":
    print("Database Migration Script - LOCALHOST (Paid Cases Only)")
    print("=" * 60)
    
    confirm = input("Are you sure you want to run this migration on localhost? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled")
        sys.exit(0)
    
    # Try Flask migration first, fall back to direct SQLite if needed
    try:
        run_flask_migration()
    except ImportError as e:
        print(f"Could not import Flask modules: {e}")
        print("Falling back to direct SQLite migration...")
        run_sqlite_migration()
    except Exception as e:
        print(f"Flask migration failed: {e}")
        print("Falling back to direct SQLite migration...")
        run_sqlite_migration()