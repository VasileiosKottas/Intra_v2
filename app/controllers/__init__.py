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

def register_controllers(app):
    """Register all controllers with the Flask app"""
    AuthController(app)
    DashboardController(app)
    MasterController(app)
    APIController(app)
    WebhookController(app)
    ReportsController(app)
    TeamReportController(app)  # Add this line
    print("All controllers registered successfully")


__all__ = [
    'register_controllers',
    'AuthController', 'DashboardController', 
    'MasterController', 'APIController',
    'WebhookController', 'ReportsController',
    'TeamReportController'  # Add this
]