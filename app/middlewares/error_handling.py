"""
Error handling middleware for global error management
"""

from flask import request, jsonify

class ErrorHandlingMiddleware:
    """Middleware for global error handling"""
    
    def __init__(self, app):
        self.app = app
        self.setup_error_handlers()
    
    def setup_error_handlers(self):
        """Setup global error handlers"""
        @self.app.errorhandler(404)
        def not_found(error):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Resource not found'}), 404
            return "Page not found", 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Internal server error'}), 500
            return "Internal server error", 500
        
        @self.app.errorhandler(403)
        def forbidden(error):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Access forbidden'}), 403
            return "Access forbidden", 403