"""
Security middleware for headers and CORS with iframe support
"""

from flask import request

class SecurityMiddleware:
    """Middleware for security headers and CORS with iframe embedding support"""
    
    def __init__(self, app):
        self.app = app
        self.setup_security_headers()
    
    def setup_security_headers(self):
        """Setup security headers with iframe support"""
        @self.app.after_request
        def add_security_headers(resp):
            # Basic security headers
            resp.headers['X-Content-Type-Options'] = 'nosniff'
            resp.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Check if request is from WordPress iframe
            referer = request.headers.get('Referer', '')
            is_iframe_context = (
                'iframe=1' in request.args or 
                'windsorhillmortgages.co.uk' in referer or
                request.headers.get('Sec-Fetch-Dest') == 'iframe'
            )
            
            if is_iframe_context:
                # Allow iframe embedding for WordPress integration
                resp.headers['X-Frame-Options'] = 'ALLOWALL'
                resp.headers['Content-Security-Policy'] = "frame-ancestors https://windsorhillmortgages.co.uk https://www.windsorhillmortgages.co.uk;"
                
                # Handle iframe-specific cookie settings for session persistence
                set_cookie_header = resp.headers.get('Set-Cookie', '')
                if set_cookie_header:
                    # Ensure SameSite=None for iframe context
                    if 'SameSite=' in set_cookie_header:
                        set_cookie_header = set_cookie_header.replace('SameSite=Lax', 'SameSite=None; Secure')
                        set_cookie_header = set_cookie_header.replace('SameSite=Strict', 'SameSite=None; Secure')
                    else:
                        # Add SameSite=None if not present
                        if 'Secure' not in set_cookie_header:
                            set_cookie_header += '; Secure'
                        set_cookie_header += '; SameSite=None'
                    
                    resp.headers['Set-Cookie'] = set_cookie_header
                
                print(f"🖼️  iFrame request handled: {request.method} {request.path}")
            else:
                # Standard security for non-iframe requests
                resp.headers['X-Frame-Options'] = 'DENY'
            
            # Only add HTTPS headers if not in development
            if not self.app.debug:
                resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return resp