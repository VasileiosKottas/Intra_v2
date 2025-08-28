"""
Configuration manager for application settings
"""

import os
from typing import Dict, List, Optional
from app.config.companies import CompanyConfig, WINDSOR_CONFIG, CNC_CONFIG

class ConfigurationManager:
    """Manages all company configurations and application settings"""
    
    def __init__(self):
        self._companies = self._initialize_company_configs()
        self._app_config = self._initialize_app_config()
    
    def _initialize_company_configs(self) -> Dict[str, CompanyConfig]:
        """Initialize company-specific configurations"""
        return {
            'windsor': WINDSOR_CONFIG,
            'cnc': CNC_CONFIG
        }
    
    def _initialize_app_config(self) -> Dict:
        """Initialize application-wide configuration"""
        return {
            # Existing JotForm config
            'JOTFORM_API_KEY': os.getenv('JOTFORM_API_KEY', 'b78b083ca0a78392acf8de69666a3577'),
            'SUBMISSION_FORM_ID': "250232251408041",
            'PAID_FORM_ID': "251406545360048",
            'BASE_URL': "https://eu-api.jotform.com",
            
            # Add Calendly configuration
            'CALENDLY_ACCESS_TOKEN': 'eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzU2MzAxNTk2LCJqdGkiOiI3NjFjNTIzOC1jZWZjLTRkNTAtYjBhMi1kNjdkNjFmZTczMzQiLCJ1c2VyX3V1aWQiOiJiNDNiYmJlNS1hNDEwLTQ0YTctYjIwNS1lMzk2N2ExNTgxYTkifQ.GvnP5kkXUfWk9SLHDzkhFnzbLyWBcD3ipCCq5I4tUt0OVFqOOXoFcw1WWsyCr4POLKd_fB-oQaSCearT3SyKyw',            
            # Other existing config
            'SYNC_HOURS': [9, 17],
            'SYNC_INTERVAL_MINUTES': 120,
            'DEFAULT_YEARLY_GOAL': 50000.0,
            'DEFAULT_TEAM_GOAL': 50000.0
        }
    
    def get_company_config(self, company: str) -> Optional[CompanyConfig]:
        """Get configuration for a specific company"""
        return self._companies.get(company.lower())
    
    def get_all_companies(self) -> List[str]:
        """Get list of all available companies"""
        return list(self._companies.keys())
    
    def get_app_config(self, key: str, default=None):
        """Get application configuration value"""
        return self._app_config.get(key, default)
    
    def is_valid_company(self, company: str) -> bool:
        """Check if company is valid"""
        return company.lower() in self._companies
    
    # Convenience methods for common operations
    def get_valid_business_types(self, company: str) -> List[str]:
        """Get valid business types for company"""
        config = self.get_company_config(company)
        return config.valid_business_types if config else []
    
    def get_valid_paid_case_types(self, company: str) -> List[str]:
        """Get valid paid case types for company"""
        config = self.get_company_config(company)
        return config.valid_paid_case_types if config else []
    
    def get_advisor_names(self, company: str) -> List[str]:
        """Get advisor names for company"""
        config = self.get_company_config(company)
        return config.advisor_names if config else []
    
    def normalize_advisor_name(self, company: str, name: str) -> Optional[str]:
        """Normalize advisor name for company"""
        config = self.get_company_config(company)
        return config.normalize_advisor_name(name) if config else None
