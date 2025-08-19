"""
Security middleware for headers and CORS
"""

from flask import request

class SecurityMiddleware:
    """Middleware for security headers and CORS"""
    
    def __init__(self, app):
        self.app = app
        self.setup_security_headers()
    
    def setup_security_headers(self):
        """Setup security headers"""
        @self.app.after_request
        def add_security_headers(resp):
            # Basic security headers
            resp.headers['X-Content-Type-Options'] = 'nosniff'
            resp.headers['X-Frame-Options'] = 'DENY'
            resp.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Only add HTTPS headers if not in development
            if not self.app.debug:
                resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return resp