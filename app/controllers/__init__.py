"""
Controllers package
Exports all route controllers and registration function
"""

from .auth import AuthController
from .dashboard import DashboardController
from .master import MasterController
from .api import APIController
from .webhook_controller import WebhookController

def register_controllers(app):
    """Register all controllers with the Flask app"""
    AuthController(app)
    DashboardController(app)
    MasterController(app)
    APIController(app)
    WebhookController(app)
    print(" All controllers registered successfully")

__all__ = [
    'register_controllers',
    'AuthController', 'DashboardController', 
    'MasterController', 'APIController',
    'WebhookController'
]