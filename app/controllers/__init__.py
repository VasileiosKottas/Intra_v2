"""
Controllers package
Exports all route controllers and registration function
"""

from .auth import AuthController
from .dashboard import DashboardController
from .master import MasterController
from .api import APIController
from .webhook_controller import WebhookController
from .reports_controller import ReportsController
from .calendly_controller import CalendlyController  # Add this import
from .team_report_controller import TeamReportController
from .enhanced_team_controller import EnhancedTeamReportController
from .email_config_controller import EmailConfigController
def register_controllers(app):
    """Register all controllers with the Flask app"""
    AuthController(app)
    DashboardController(app)
    MasterController(app)
    APIController(app)
    WebhookController(app)
    ReportsController(app)
    EnhancedTeamReportController(app)  # Add this line
    CalendlyController(app)
    EmailConfigController(app)
    print("All controllers registered successfully")


__all__ = [
    'register_controllers',
    'AuthController', 'DashboardController', 
    'MasterController', 'APIController',
    'WebhookController', 'ReportsController',
    'TeamReportController', 'CalendlyController',
    'EmailConfigController', 'EnhancedTeamReportController'  # Add this
]