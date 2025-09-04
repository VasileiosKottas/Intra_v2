"""
Main application class - orchestrates all components
"""

import threading
from app import create_app
from app.services.sync import AutoSyncManager

def register_team_report_routes(app):
    """Register team performance report routes"""
    from app.controllers.team_report_controller import TeamReportController
    
    try:
        team_report_controller = TeamReportController(app)
        team_report_controller.register_routes()
        print("Team report routes registered successfully")
    except Exception as e:
        print(f"Error registering team report routes: {e}")

def register_email_config_routes(app):
    """Register email configuration routes"""
    from app.controllers.email_config_controller import EmailConfigController
    
    try:
        email_config_controller = EmailConfigController(app)
        email_config_controller.register_routes()
        print("✅ Email configuration routes registered successfully")
    except Exception as e:
        print(f"❌ Error registering email config routes: {e}")


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
        """Start hybrid sync services - webhooks + daily backup + email scheduler"""
        import os
        
        # Check if we should disable all sync for development
        disable_sync = os.getenv('DISABLE_ALL_SYNC', 'false').lower() == 'true'
        
        if disable_sync:
            print("All sync disabled for development. Use manual sync from master dashboard.")
            # Still start email scheduler even if sync is disabled
            self._start_email_scheduler()
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
        
        # Start email scheduler
        self._start_email_scheduler()

    def _start_email_scheduler(self):
        """Start the email report scheduler"""
        try:
            from app.services.scheduler_service import report_scheduler
            report_scheduler.start_scheduler()
            print("✅ Email report scheduler started successfully")
        except Exception as e:
            print(f"⚠️ Email scheduler not started: {e}")
            print("   Check SMTP configuration in .env file")

    def _stop_background_services(self):
        """Stop all background services"""
        # Stop sync manager
        if self.sync_manager:
            try:
                # Add stop method call if your sync manager has one
                # self.sync_manager.stop()
                pass
            except Exception as e:
                print(f"Error stopping sync manager: {e}")
        
        # Stop email scheduler
        try:
            from app.services.scheduler_service import report_scheduler
            report_scheduler.stop_scheduler()
            print("Email scheduler stopped")
        except Exception as e:
            print(f"Error stopping email scheduler: {e}")

    def run(self, debug=True, host='0.0.0.0', port=5000):
        """Run the application"""
        # Initialize database
        self.initialize_database()
        
        # Register all routes
        with self.app.app_context():
            register_team_report_routes(self.app)
            register_email_config_routes(self.app)  # Add email routes
        
        # Start background services
        self.start_background_services()
        
        print("📊 Sales Dashboard System starting...")
        print(f"🌐 Dashboard available at http://{host}:{port}")
        print(f"📧 Email config available at http://{host}:{port}/master/email-config")
        
        try:
            self.app.run(
                debug=debug, 
                host=host, 
                port=port, 
                use_reloader=False
            )
        except KeyboardInterrupt:
            print("\n🛑 Shutting down gracefully...")
        finally:
            # Cleanup on shutdown
            self._stop_background_services()
            print("✅ Shutdown complete")