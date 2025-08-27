#!/usr/bin/env python3
"""
Complete Database Migration Script - Add missing columns
"""

import os
import sys
import sqlite3
from pathlib import Path

def get_database_path():
    """Get the SQLite database path"""
    instance_path = Path(__file__).parent / "instance" / "sales_dashboard.db"
    
    if instance_path.exists():
        return str(instance_path)
    
    alt_paths = [
        Path(__file__).parent / "sales_dashboard.db",
        Path(__file__).parent / "app" / "sales_dashboard.db",
        Path(__file__).parent / "data" / "sales_dashboard.db"
    ]
    
    for path in alt_paths:
        if path.exists():
            return str(path)
    
    instance_path.parent.mkdir(parents=True, exist_ok=True)
    return str(instance_path)

def run_complete_migration():
    """Add all missing columns to paid_cases table"""
    
    db_path = get_database_path()
    print(f"Database path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Warning: Database file not found at {db_path}")
        return
    
    try:
        print("Starting complete database migration...")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns in paid_cases
        cursor.execute("PRAGMA table_info(paid_cases)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Existing paid_cases columns: {existing_columns}")
        
        # Add missing columns
        columns_to_add = {
            'who_referred': 'TEXT',
            'income_type': 'TEXT'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                print(f"Adding {column_name} column...")
                cursor.execute(f"""
                    ALTER TABLE paid_cases 
                    ADD COLUMN {column_name} {column_type};
                """)
                print(f"Added {column_name} column")
            else:
                print(f"{column_name} column already exists")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(paid_cases)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"Final paid_cases columns: {final_columns}")
        
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    print("Complete Database Migration Script")
    print("=" * 40)
    
    confirm = input("Run migration to add missing columns? (yes/no): ")
    if confirm.lower() == 'yes':
        run_complete_migration()
    else:
        print("Migration cancelled")