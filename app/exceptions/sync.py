"""
Synchronization operation exceptions
"""

from .base import SalesDashboardException

class SyncError(SalesDashboardException):
    """Exception raised during sync operations"""
    
    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        super().__init__(message, 'SYNC_ERROR')

class JotFormAPIError(SyncError):
    """Exception raised for JotForm API errors"""
    
    def __init__(self, message: str, status_code: int = None, response_data=None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message, 'JOTFORM_API_ERROR')
    
    def to_dict(self):
        result = super().to_dict()
        if self.status_code:
            result['status_code'] = self.status_code
        if self.response_data:
            result['response_data'] = self.response_data
        return result

class NetworkError(SyncError):
    """Exception raised for network-related sync errors"""
    
    def __init__(self, message: str = "Network connection error"):
        super().__init__(message, 'NETWORK_ERROR')


class DataProcessingError(SyncError):
    """Exception raised when processing synced data fails"""
    
    def __init__(self, message: str, record_id: str = None):
        self.record_id = record_id
        super().__init__(message, 'DATA_PROCESSING_ERROR')