"""
Custom exception classes for the application
"""

from .base import SalesDashboardException, ValidationError
from .auth import AuthenticationError, AuthorizationError
from .data import DataValidationError, DataSyncError
from .sync import SyncError, JotFormAPIError

__all__ = [
    'SalesDashboardException', 'ValidationError',
    'AuthenticationError', 'AuthorizationError',
    'DataValidationError', 'DataSyncError',
    'SyncError', 'JotFormAPIError'
]