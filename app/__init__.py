"""
Sales Dashboard Application Package
Entry point for the Flask application with factory pattern
"""

import os
from flask import Flask
from flask_cors import CORS

def create_app(config_name='development'):
    """Application factory function"""
    
    # Get the correct template and static directories
    # This ensures Flask looks in the right place for templates and static files
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Load configuration
    load_config(app, config_name)
    
    # ADD IFRAME SESSION SUPPORT HERE:
    configure_iframe_support(app)
    
    # Setup CORS with iframe support
    setup_cors(app)
        
    # Initialize database
    from app.models import init_db
    init_db(app)
    
    # Setup middlewares
    from app.middlewares import setup_middlewares
    setup_middlewares(app)
    
    # Register controllers
    from app.controllers import register_controllers
    register_controllers(app)
    
    return app

def configure_iframe_support(app):
    """Configure Flask for iframe embedding support"""
    
    # Session configuration for iframe compatibility
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cross-domain
    
    print("✓ Configured iframe session support")

def setup_cors(app):
    """Setup CORS with iframe and credentials support"""
    
    origins = os.getenv('CORS_ORIGINS', '*')
    
    # Parse origins from environment variable
    if origins == '*':
        allowed_origins = [
            "https://windsorhillmortgages.co.uk",
            "https://www.windsorhillmortgages.co.uk",
            "https://sales-dashboard-5g5x.onrender.com"
        ]
    else:
        allowed_origins = [o.strip() for o in origins.split(',') if o.strip()]
    
    # Add your specific WordPress paths
    wordpress_origins = []
    for origin in allowed_origins:
        if 'windsorhillmortgages.co.uk' in origin:
            wordpress_origins.extend([
                origin,
                f"{origin}/winsuite",
                f"{origin}/dashboard",
                f"{origin}/sales-dashboard"
            ])
        else:
            wordpress_origins.append(origin)
    
    CORS(app, resources={
        r"/api/*": {
            "origins": wordpress_origins,
            "supports_credentials": True,
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        },
        r"/*": {  # Allow all routes for iframe embedding
            "origins": wordpress_origins,
            "supports_credentials": True
        }
    }, supports_credentials=True)
    
    print(f"✓ Configured CORS for origins: {wordpress_origins}")

def load_config(app, config_name='development'):
    """Load configuration into Flask app"""
    
    # Detect if running on Render
    if os.environ.get('RENDER'):
        config_name = 'production'
    
    # Base configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, "..", "instance", "sales_dashboard.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    configs = {
        'development': {
            'DEBUG': True,
            'SQLALCHEMY_DATABASE_URI': f"sqlite:///{db_path}",
            'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        },
        'testing': {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        },
        'production': {
            'DEBUG': False,
            'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', f"sqlite:///{db_path}"),
            'SECRET_KEY': os.getenv('SECRET_KEY'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        }
    }
    
    app.config.update(configs.get(config_name, configs['development']))
    print(f"✓ Loaded {config_name} configuration")
    print(f"✓ Template folder: {app.template_folder}")
    print(f"✓ Static folder: {app.static_folder}")