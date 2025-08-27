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
        """Start hybrid sync services - webhooks + daily backup"""
        import os
        
        # Check if we should disable all sync for development
        disable_sync = os.getenv('DISABLE_ALL_SYNC', 'false').lower() == 'true'
        
        if disable_sync:
            print("All sync disabled for development. Use manual sync from master dashboard.")
            return
        
        # Initialize sync manager with app context
        self.sync_manager = AutoSyncManager(self.app)
        
        # Skip initial sync - webhooks will handle real-time data
        # Only do initial sync if explicitly requested
        do_initial_sync = os.getenv('DO_INITIAL_SYNC', 'false').lower() == 'true'
        
        if do_initial_sync:
            print("Performing initial sync...")
            with self.app.app_context():
                self.sync_manager.backup_sync_all_companies()
        else:
            print("Skipping initial sync - using webhooks for real-time data")
        
        # Setup hybrid scheduler (daily backup + weekly integrity check)
        self.sync_manager.setup_hybrid_scheduler()
        
        # Start scheduler thread
        threading.Thread(
            target=self.sync_manager.run_scheduler, 
            daemon=True
        ).start()
        
        print("Hybrid sync system started:")
        print("  - Real-time data via webhooks")
        print("  - Daily backup sync at 2:00 AM") 
        print("  - Weekly integrity checks")
        
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