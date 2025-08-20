# ===== scripts/create_master_user.py (FIXED) =====
#!/usr/bin/env python3
"""
Script to create master user
"""

import sys
import os

# Add the parent directory to the path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.services.database import DatabaseService

def main():
    """Create master user"""
    print("🚀 Initializing database and creating master user...")
    
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        db_service = DatabaseService()
        
        print("📊 Creating database tables...")
        db_service.create_tables()
        
        print("👑 Creating master user...")
        db_service.create_master_user()
        
        print("✅ Setup completed successfully!")
        print("👑 Master user login details:")
        print("   Username: master")
        print("   Password: master123")

if __name__ == '__main__':
    main()

# ===== scripts/setup_database.py (NEW) =====
#!/usr/bin/env python3
"""
Complete database setup script - creates tables, master user, and sample data
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.services.database import DatabaseService

def main():
    """Complete database setup"""
    print("🚀 Starting complete database setup...")
    
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        db_service = DatabaseService()
        
        print("\n📊 Step 1: Creating database tables...")
        db_service.create_tables()
        print("✅ Database tables created successfully!")
        
        print("\n👑 Step 2: Creating master user...")
        db_service.create_master_user()
        print("✅ Master user created successfully!")
        
        print("\n👥 Step 3: Creating sample data...")
        response = input("Do you want to create sample data (advisors and teams)? (y/n): ")
        if response.lower() in ['y', 'yes']:
            db_service.create_sample_data()
            print("✅ Sample data created successfully!")
        else:
            print("⏭️ Skipping sample data creation")
        
        print("\n🎉 Database setup completed!")
        print("\n📋 Login Information:")
        print("   👑 Master user:")
        print("      Username: master")
        print("      Password: master123")
        
        if response.lower() in ['y', 'yes']:
            print("\n   👥 Sample advisor accounts:")
            print("      Username: jamie, steven, daniel, drew, michael, etc.")
            print("      Password: password123 (for all sample accounts)")
        
        print(f"\n🌐 Start the application with: python run.py")
        print(f"📊 Then visit: http://localhost:5000")

if __name__ == '__main__':
    main()

# ===== scripts/reset_database.py (NEW) =====
#!/usr/bin/env python3
"""
Script to reset the database (delete and recreate)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp

def main():
    """Reset the database"""
    print("⚠️ WARNING: This will delete all existing data!")
    response = input("Are you sure you want to reset the database? (y/n): ")
    
    if response.lower() not in ['y', 'yes']:
        print("❌ Database reset cancelled")
        return
    
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        from app.models import db
        
        print("🗑️ Dropping all tables...")
        db.drop_all()
        
        print("📊 Creating fresh tables...")
        db.create_all()
        
        print("✅ Database reset completed!")
        print("💡 Run 'python scripts/setup_database.py' to set up the database with initial data")

if __name__ == '__main__':
    main()

# ===== app/services/database.py (UPDATED with better error handling) =====
"""
Database service for operations and initialization
"""

from werkzeug.security import generate_password_hash
from app.models import db
from app.models.advisor import Advisor
from app.models.team import Team
from app.config import config_manager

class DatabaseService:
    """Service for database operations and initialization"""
    
    def create_tables(self):
        """Create all database tables"""
        try:
            db.create_all()
            print("📊 Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            raise
    
    def create_master_user(self):
        """Create master user if it doesn't exist"""
        try:
            # Check if master user already exists
            master = Advisor.query.filter_by(is_master=True).first()
            if master:
                print(f"👑 Master user already exists: {master.username}")
                return master
            
            # Create new master user
            master = Advisor(
                full_name='Master Administrator',
                username='master',
                email='master@houseofwindsor.com',
                password_hash=generate_password_hash('master123'),
                is_master=True
            )
            master.save()
            print("👑 Master user created: username='master', password='master123'")
            return master
            
        except Exception as e:
            print(f"❌ Error creating master user: {e}")
            raise
    
    def create_sample_data(self):
        """Create sample data for testing"""
        try:
            # Check if sample data already exists
            if Advisor.query.filter_by(full_name='Jamie Cope').first():
                print("📋 Sample data already exists")
                return
            
            print("🏗️ Creating sample data...")
            
            # Create sample advisors
            advisors_data = [
                {'full_name': 'Jamie Cope', 'username': 'jamie', 'email': 'jamie@houseofwindsor.com'},
                {'full_name': 'Daniel Jones', 'username': 'daniel', 'email': 'daniel@houseofwindsor.com'},
                {'full_name': 'Drew Gibson', 'username': 'drew', 'email': 'drew@houseofwindsor.com'},
                {'full_name': 'Michael Olivieri', 'username': 'michael', 'email': 'michael@houseofwindsor.com'},
                {'full_name': 'Oliver Cotterell', 'username': 'oliver', 'email': 'oliver@houseofwindsor.com'},
                {'full_name': 'Elliot Cotterell', 'username': 'elliot', 'email': 'elliot@houseofwindsor.com'},
                {'full_name': 'Lottie Brown', 'username': 'lottie', 'email': 'lottie@houseofwindsor.com'},
                {'full_name': 'Martyn Barberry', 'username': 'martyn', 'email': 'martyn@houseofwindsor.com'},
                {'full_name': 'Nick Snailum (Referral)', 'username': 'nick', 'email': 'nick@houseofwindsor.com'}
            ]
            
            created_advisors = []
            for advisor_data in advisors_data:
                # Check if advisor already exists
                existing = Advisor.query.filter_by(username=advisor_data['username']).first()
                if existing:
                    print(f"⏭️ Advisor {advisor_data['username']} already exists, skipping...")
                    created_advisors.append(existing)
                    continue
                
                advisor = Advisor(
                    full_name=advisor_data['full_name'],
                    username=advisor_data['username'],
                    email=advisor_data['email'],
                    password_hash=generate_password_hash('password123'),
                    is_master=False
                )
                advisor.save()
                created_advisors.append(advisor)
                print(f"✅ Created advisor: {advisor_data['full_name']}")
            
            # Create teams for both companies
            teams_to_create = [
                {
                    'name': 'Sales Team Alpha',
                    'monthly_goal': 50000.0,
                    'company': 'windsor',
                    'is_hidden': False
                },
                {
                    'name': 'Performance Tracking',
                    'monthly_goal': 30000.0,
                    'company': 'windsor',
                    'is_hidden': True
                },
                {
                    'name': 'CnC Development Team',
                    'monthly_goal': 40000.0,
                    'company': 'cnc',
                    'is_hidden': False
                }
            ]
            
            created_teams = []
            for team_data in teams_to_create:
                # Check if team already exists
                existing_team = Team.query.filter_by(
                    name=team_data['name'],
                    company=team_data['company']
                ).first()
                
                if existing_team:
                    print(f"⏭️ Team {team_data['name']} already exists, skipping...")
                    created_teams.append(existing_team)
                    continue
                
                # Get master user ID for created_by
                master = Advisor.query.filter_by(is_master=True).first()
                if not master:
                    print("❌ Master user not found, cannot create teams")
                    continue
                
                team = Team(
                    name=team_data['name'],
                    monthly_goal=team_data['monthly_goal'],
                    created_by=master.id,
                    company=team_data['company'],
                    is_hidden=team_data['is_hidden']
                )
                team.save()
                created_teams.append(team)
                print(f"✅ Created team: {team_data['name']} ({team_data['company']})")
            
            # Assign advisors to teams
            if created_advisors and created_teams:
                windsor_team = next((t for t in created_teams if t.company == 'windsor' and not t.is_hidden), None)
                cnc_team = next((t for t in created_teams if t.company == 'cnc'), None)
                
                # Assign first 5 advisors to Windsor team
                if windsor_team:
                    for advisor in created_advisors[:5]:
                        success, message = windsor_team.add_member(advisor, 50000.0)
                        if success:
                            print(f"✅ Assigned {advisor.full_name} to {windsor_team.name}")
                
                # Assign remaining advisors to CnC team
                if cnc_team and len(created_advisors) > 5:
                    for advisor in created_advisors[5:]:
                        success, message = cnc_team.add_member(advisor, 45000.0)
                        if success:
                            print(f"✅ Assigned {advisor.full_name} to {cnc_team.name}")
            
            print("✅ Sample data created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            raise
    
    def backfill_advisor_links(self, advisor):
        """Link existing records by exact advisor name to this advisor's ID."""
        try:
            from app.models.submission import Submission
            from app.models.paid_case import PaidCase
            
            # Submissions
            submissions = Submission.query.filter(
                Submission.advisor_name == advisor.full_name,
                Submission.advisor_id.is_(None)
            ).all()
            for submission in submissions:
                submission.advisor_id = advisor.id

            # Paid cases
            paid_cases = PaidCase.query.filter(
                PaidCase.advisor_name == advisor.full_name,
                PaidCase.advisor_id.is_(None)
            ).all()
            for paid_case in paid_cases:
                paid_case.advisor_id = advisor.id

            db.session.commit()
            print(f"🔗 Linked {len(submissions)} submissions and {len(paid_cases)} paid cases to {advisor.full_name}")
            
        except Exception as e:
            print(f"❌ Error backlinking advisor data: {e}")
            db.session.rollback()
            raise

# ===== Updated run.py with database check =====
#!/usr/bin/env python3
"""
Development entry point for the Sales Dashboard application
"""

import os
import sys
from dotenv import load_dotenv

# Ensure we're running from the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Add the current directory to Python path
sys.path.insert(0, script_dir)

# Load environment variables from .env file
load_dotenv()

from app.main import SalesDashboardApp

def check_database():
    """Check if database exists and has tables"""
    db_path = os.path.join('instance', 'sales_dashboard.db')
    if not os.path.exists(db_path):
        return False, "Database file doesn't exist"
    
    # Try to check if tables exist
    try:
        app_instance = SalesDashboardApp('development')
        with app_instance.app.app_context():
            from app.models.advisor import Advisor
            # Try to query - if this fails, tables don't exist
            Advisor.query.first()
        return True, "Database ready"
    except Exception as e:
        return False, f"Database exists but tables missing: {e}"

def main():
    """Main function to run the development server"""
    print(f" Starting from directory: {os.getcwd()}")
    
    # Check templates
    if not os.path.exists('templates'):
        print(" Templates directory not found!")
        print("Please ensure you have a 'templates' directory with your HTML files")
        return
    
    print(" Templates directory found")
    
    # Check database
    db_ready, db_message = check_database()
    if not db_ready:
        print(f" Database issue: {db_message}")
        print("\n To set up the database, run:")
        print("   python scripts/setup_database.py")
        print("\n Then restart with:")
        print("   python run.py")
        return
    
    print(f" {db_message}")
    
    # Create and run application
    app = SalesDashboardApp('development')
    
    print("\n Sales Dashboard starting in development mode...")
    print(" Dashboard available at http://localhost:5000")
    print(" Master login: username='master', password='master123'")
    
    # Run development server
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )

if __name__ == '__main__':
    main()