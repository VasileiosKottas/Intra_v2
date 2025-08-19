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
    
    # Setup CORS
    origins = os.getenv('CORS_ORIGINS', '*')
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "https://windsorhillmortgages.co.uk/winsuite",
                "https://www.windsorhillmortgages.co.uk/winsuite",
                "https://sales-dashboard-5g5x.onrender.com"
            ]
        }
    })
        
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

def load_config(app, config_name='development'):
    """Load configuration into Flask app"""
    
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
    print(f" Loaded {config_name} configuration")
    print(f" Template folder: {app.template_folder}")
    print(f" Static folder: {app.static_folder}")
