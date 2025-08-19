"""
Database service for operations and initialization - Production ready
"""

from werkzeug.security import generate_password_hash
from app.models import db
from app.models.advisor import Advisor
from app.models.team import Team
from app.config import config_manager
import os

class DatabaseService:
    """Service for database operations and initialization"""
    
    def create_tables(self):
        """Create all database tables"""
        try:
            db.create_all()
            print(" Database tables created successfully")
        except Exception as e:
            print(f" Error creating database tables: {e}")
            raise
    
    def create_master_user(self):
        """Create master user if it doesn't exist"""
        try:
            # Check if master user already exists
            master = Advisor.query.filter_by(is_master=True).first()
            if master:
                print(f" Master user already exists: {master.username}")
                return master
            
            # Use environment variable for master password in production
            master_password = os.getenv('MASTER_PASSWORD', 'master123')
            
            # Create new master user
            master = Advisor(
                full_name='Master Administrator',
                username='master',
                email='master@houseofwindsor.com',
                password_hash=generate_password_hash(master_password),
                is_master=True
            )
            master.save()
            print(" Master user created successfully")
            
            # Only show password in development
            if os.getenv('FLASK_ENV') == 'development':
                print(f" Login: username='master', password='{master_password}'")
            else:
                print(" Master user ready for production")
            
            return master
            
        except Exception as e:
            print(f" Error creating master user: {e}")
            raise
    
    def create_sample_data(self):
        """Create sample data for testing (only in development)"""
        # Only create sample data in development
        if os.getenv('FLASK_ENV') == 'production':
            print(" Skipping sample data creation in production")
            return
            
        try:
            # Check if sample data already exists
            if Advisor.query.filter_by(full_name='Jamie Cope').first():
                print(" Sample data already exists")
                return
            
            print(" Creating sample data...")
            
            # Create sample advisors
            advisors_data = [
                {'full_name': 'Jamie Cope', 'username': 'jamie', 'email': 'jamie@houseofwindsor.com'},
                {'full_name': 'Steven Horn', 'username': 'steven', 'email': 'steven@houseofwindsor.com'},
                {'full_name': 'Daniel Jones', 'username': 'daniel', 'email': 'daniel@houseofwindsor.com'},
                {'full_name': 'Drew Gibson', 'username': 'drew', 'email': 'drew@houseofwindsor.com'},
                {'full_name': 'Michael Olivieri', 'username': 'michael', 'email': 'michael@houseofwindsor.com'},
            ]
            
            created_advisors = []
            for advisor_data in advisors_data:
                # Check if advisor already exists
                existing = Advisor.query.filter_by(username=advisor_data['username']).first()
                if existing:
                    print(f" Advisor {advisor_data['username']} already exists, skipping...")
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
                print(f" Created advisor: {advisor_data['full_name']}")
            
            print(" Sample data created successfully!")
            
        except Exception as e:
            print(f" Error creating sample data: {e}")
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
            
            if submissions or paid_cases:
                print(f" Linked {len(submissions)} submissions and {len(paid_cases)} paid cases to {advisor.full_name}")
            
        except Exception as e:
            print(f" Error backlinking advisor data: {e}")
            db.session.rollback()
            raise