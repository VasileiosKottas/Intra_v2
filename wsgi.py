"""
WSGI entry point for production deployment on Render
"""

import os
from dotenv import load_dotenv
from app.main import SalesDashboardApp

# Load environment variables
load_dotenv()

# Create application for production
app_instance = SalesDashboardApp('production')

# Initialize database with tables
with app_instance.app.app_context():
    from app.models import db
    from app.services.database import DatabaseService
    
    print(" Initializing production database...")
    
    # Create all tables
    db.create_all()
    print(" Database tables created")
    
    # Create master user if it doesn't exist
    db_service = DatabaseService()
    try:
        db_service.create_master_user()
        print(" Master user ready")
    except Exception as e:
        print(f" Master user setup: {e}")

# Start background services
app_instance.start_background_services()
print(" Background sync services started")

# Export the Flask app for WSGI servers
app = app_instance.app

if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
