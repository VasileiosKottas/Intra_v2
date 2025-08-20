# Create this file as: scripts/check_database.py

#!/usr/bin/env python3
"""
Script to check database contents and verify users
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models.advisor import Advisor
from werkzeug.security import check_password_hash

def main():
    """Check database contents"""
    print("🔍 Checking database contents...")
    
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        try:
            # Check all users
            all_users = Advisor.query.all()
            print(f"\n📊 Total users in database: {len(all_users)}")
            
            for user in all_users:
                print(f"  - ID: {user.id}, Username: {user.username}, Name: {user.full_name}, Master: {user.is_master}")
            
            # Check master user specifically
            master = Advisor.query.filter_by(username='master').first()
            if master:
                print(f"\n👑 Master user found:")
                print(f"  - ID: {master.id}")
                print(f"  - Username: {master.username}")
                print(f"  - Full Name: {master.full_name}")
                print(f"  - Is Master: {master.is_master}")
                
                # Test password
                password_test = check_password_hash(master.password_hash, 'master123')
                print(f"  - Password 'master123' works: {password_test}")
                
            else:
                print("\n❌ No master user found!")
                print("Creating master user...")
                
                from app.services.database import DatabaseService
                db_service = DatabaseService()
                db_service.create_master_user()
                print("✅ Master user created!")
            
            print(f"\n🔍 Session test:")
            print("Try logging in with:")
            print("  Username: master")
            print("  Password: master123")
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()