"""
Middlewares package
Exports middleware setup function
"""

from .cache import CacheMiddleware
from .security import SecurityMiddleware
from .logging import LoggingMiddleware
from .error_handling import ErrorHandlingMiddleware

def setup_middlewares(app):
    """Setup all middlewares for the application"""
    CacheMiddleware(app)
    SecurityMiddleware(app)
    LoggingMiddleware(app)
    ErrorHandlingMiddleware(app)
    
    print(" All middlewares configured successfully")

__all__ = [
    'setup_middlewares',
    'CacheMiddleware', 'SecurityMiddleware', 
    'LoggingMiddleware', 'ErrorHandlingMiddleware'
]