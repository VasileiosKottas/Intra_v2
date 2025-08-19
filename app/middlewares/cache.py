"""
Cache middleware for handling caching headers
"""

from flask import request

class CacheMiddleware:
    """Middleware for handling caching headers"""
    
    def __init__(self, app):
        self.app = app
        self.setup_cache_headers()
    
    def setup_cache_headers(self):
        """Setup cache control headers for API routes"""
        @self.app.after_request
        def add_no_cache_headers(resp):
            if request.path.startswith('/api/'):
                resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                resp.headers['Pragma'] = 'no-cache'
                resp.headers['Expires'] = '0'
            return resp