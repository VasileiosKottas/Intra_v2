"""
Authentication and authorization exceptions
"""

from .base import SalesDashboardException

class AuthenticationError(SalesDashboardException):
    """Exception raised for authentication failures"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 'AUTH_ERROR')

class AuthorizationError(SalesDashboardException):
    """Exception raised for authorization failures"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 'AUTHORIZATION_ERROR')

class InvalidCredentialsError(AuthenticationError):
    """Exception raised for invalid login credentials"""
    
    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message)

class SessionExpiredError(AuthenticationError):
    """Exception raised when user session has expired"""
    
    def __init__(self, message: str = "Your session has expired. Please log in again."):
        super().__init__(message)