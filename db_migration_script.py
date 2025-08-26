#!/usr/bin/env python3
"""
Database Migration Script for Adding income_type Column
Run this on Render to update your database schema
"""

import os
import sys
from sqlalchemy import text
from app import create_app
from app.models import db

def run_migration():
    """Run the database migration to add income_type columns"""
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting database migration...")
            
            # Check if columns already exist
            print("Checking existing schema...")
            
            # Check submissions table
            result = db.engine.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'submissions' 
                AND column_name = 'income_type';
            """)).fetchone()
            
            submissions_has_income_type = result is not None
            
            # Check paid_cases table  
            result = db.engine.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paid_cases' 
                AND column_name = 'income_type';
            """)).fetchone()
            
            paid_cases_has_income_type = result is not None
            
            print(f"Submissions table has income_type: {submissions_has_income_type}")
            print(f"Paid_cases table has income_type: {paid_cases_has_income_type}")
            
            # Add income_type to submissions table if not exists
            if not submissions_has_income_type:
                print("Adding income_type column to submissions table...")
                db.engine.execute(text("""
                    ALTER TABLE submissions 
                    ADD COLUMN income_type VARCHAR(100);
                """))
                print("✅ Added income_type column to submissions table")
            else:
                print("ℹ️  income_type column already exists in submissions table")
            
            # Add income_type to paid_cases table if not exists
            if not paid_cases_has_income_type:
                print("Adding income_type column to paid_cases table...")
                db.engine.execute(text("""
                    ALTER TABLE paid_cases 
                    ADD COLUMN income_type VARCHAR(100);
                """))
                print("✅ Added income_type column to paid_cases table")
            else:
                print("ℹ️  income_type column already exists in paid_cases table")
            
            # Commit the changes
            db.session.commit()
            print("✅ Migration completed successfully!")
            
            # Verify the changes
            print("\nVerifying migration...")
            
            # Check submissions table structure
            result = db.engine.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'submissions' 
                AND column_name IN ('income_type', 'business_type', 'customer_name')
                ORDER BY column_name;
            """)).fetchall()
            
            print("Submissions table columns:")
            for row in result:
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
            
            # Check paid_cases table structure  
            result = db.engine.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'paid_cases' 
                AND column_name IN ('income_type', 'case_type', 'who_referred')
                ORDER BY column_name;
            """)).fetchall()
            
            print("Paid_cases table columns:")
            for row in result:
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    print("Database Migration Script")
    print("=" * 40)
    
    # Check if we're in the right environment
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable not found")
        print("Make sure you're running this on Render or with proper environment setup")
        sys.exit(1)
    
    confirm = input("Are you sure you want to run this migration? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled")
        sys.exit(0)
    
    run_migration()