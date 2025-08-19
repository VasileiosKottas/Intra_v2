"""
Base exception classes
"""

class SalesDashboardException(Exception):
    """Base exception for Sales Dashboard application"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert exception to dictionary for JSON responses"""
        return {
            'error': self.message,
            'error_code': self.error_code,
            'type': self.__class__.__name__
        }

class ValidationError(SalesDashboardException):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, 'VALIDATION_ERROR')
    
    def to_dict(self):
        result = super().to_dict()
        if self.field:
            result['field'] = self.field
        return result
