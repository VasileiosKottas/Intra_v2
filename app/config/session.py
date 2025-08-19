"""
Session management for company context
"""

from typing import Optional
from app.config.companies import CompanyConfig

class SessionManager:
    """Manages session-specific data and company context"""
    
    @staticmethod
    def get_current_company(session) -> str:
        """Get current company from session, default to windsor"""
        return session.get('company_mode', 'windsor')
    
    @staticmethod
    def set_current_company(session, company: str) -> bool:
        """Set current company in session"""
        from app.config.settings import ConfigurationManager
        config_manager = ConfigurationManager()
        
        if config_manager.is_valid_company(company):
            session['company_mode'] = company
            return True
        return False
    
    @staticmethod
    def get_company_config(session) -> Optional[CompanyConfig]:
        """Get configuration for current company in session"""
        from app.config.settings import ConfigurationManager
        config_manager = ConfigurationManager()
        
        current_company = SessionManager.get_current_company(session)
        return config_manager.get_company_config(current_company)