"""
Data validation and processing exceptions
"""

from .base import SalesDashboardException, ValidationError

class DataValidationError(ValidationError):
    """Exception raised for data validation errors"""
    
    def __init__(self, message: str, field: str = None, value=None):
        self.value = value
        super().__init__(message, field)

class DataSyncError(SalesDashboardException):
    """Exception raised during data synchronization"""
    
    def __init__(self, message: str, source: str = None):
        self.source = source
        super().__init__(message, 'DATA_SYNC_ERROR')

class InvalidDateError(DataValidationError):
    """Exception raised for invalid date formats"""
    
    def __init__(self, date_value: str, field: str = 'date'):
        message = f"Invalid date format: {date_value}"
        super().__init__(message, field, date_value)

class InvalidCurrencyError(DataValidationError):
    """Exception raised for invalid currency amounts"""
    
    def __init__(self, currency_value: str, field: str = 'amount'):
        message = f"Invalid currency amount: {currency_value}"
        super().__init__(message, field, currency_value)
