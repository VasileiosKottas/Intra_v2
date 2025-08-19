"""
Logging middleware for request/response logging
"""

from flask import request

class LoggingMiddleware:
    """Middleware for request logging"""
    
    def __init__(self, app):
        self.app = app
        self.setup_logging()
    
    def setup_logging(self):
        """Setup request logging"""
        @self.app.before_request
        def log_request_info():
            if self.app.debug and request.path.startswith('/api/'):
                print(f" {request.method} {request.path} - {request.remote_addr}")
        
        @self.app.after_request
        def log_response_info(resp):
            if self.app.debug and request.path.startswith('/api/'):
                print(f" {request.method} {request.path} - {resp.status_code}")
            return resp