"""
Main application class - orchestrates all components
"""

import threading
from app import create_app
from app.services.sync import AutoSyncManager

class SalesDashboardApp:
    """Main application class that orchestrates all components"""
    
    def __init__(self, config_name='development'):
        self.app = create_app(config_name)
        self.sync_manager = None
        
    def initialize_database(self):
        """Initialize database with tables and sample data"""
        from app.services.database import DatabaseService
        
        with self.app.app_context():
            db_service = DatabaseService()
            db_service.create_tables()
            # Uncomment for initial setup:
            # db_service.create_master_user()
            # db_service.create_sample_data()
            
    def start_background_services(self):
        """Start background sync services"""
        self.sync_manager = AutoSyncManager()
        
        # Initial sync
        with self.app.app_context():
            self.sync_manager.sync_all_companies()
        
        # Setup and start scheduler
        self.sync_manager.setup_scheduler()
        threading.Thread(
            target=self.sync_manager.run_scheduler, 
            daemon=True
        ).start()
        
    def run(self, debug=True, host='0.0.0.0', port=5000):
        """Run the application"""
        self.initialize_database()
        self.start_background_services()
        
        print(" Sales Dashboard System starting...")
        print(f" Dashboard available at http://{host}:{port}")
        
        self.app.run(
            debug=debug, 
            host=host, 
            port=port, 
            use_reloader=False
        )