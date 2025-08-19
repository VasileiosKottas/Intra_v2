"""
Configuration package - Updated for production deployment
"""

import os
from .settings import ConfigurationManager
from .session import SessionManager

# Global configuration instance
config_manager = ConfigurationManager()

def load_config(app, config_name='development'):
    """Load configuration into Flask app"""
    
    # Base configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    configs = {
        'development': {
            'DEBUG': True,
            'SQLALCHEMY_DATABASE_URI': _get_dev_database_url(basedir),
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
            'SQLALCHEMY_DATABASE_URI': _get_production_database_url(basedir),
            'SECRET_KEY': os.getenv('SECRET_KEY'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_pre_ping': True,
                'pool_recycle': 300,
            }
        }
    }
    
    app.config.update(configs.get(config_name, configs['development']))
    print(f"⚙️ Loaded {config_name} configuration")

def _get_dev_database_url(basedir):
    """Get development database URL"""
    db_path = os.path.join(basedir, "..", "..", "instance", "sales_dashboard.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"

def _get_production_database_url(basedir):
    """Get production database URL with fallback"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Render provides postgres:// but SQLAlchemy 1.4+ requires postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    
    # Fallback to SQLite for production if no PostgreSQL available
    db_path = os.path.join(basedir, "..", "..", "instance", "sales_dashboard.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"

__all__ = ['config_manager', 'SessionManager', 'load_config']
