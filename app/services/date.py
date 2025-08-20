"""
Date service for date operations and period calculations
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import calendar

class DateService:
    """Service for date operations and period calculations"""
    
    @staticmethod
    def parse_date(date_string: str) -> Optional[datetime.date]:
        """Parse date string to date object"""
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def resolve_period_dates(period: str, start_str: str = None, end_str: str = None) -> Tuple[datetime.date, datetime.date]:
        """Resolve period dates with support for custom range"""
        today = datetime.now().date()
        
        if period == 'custom' and start_str and end_str:
            start = DateService.parse_date(start_str)
            end = DateService.parse_date(end_str)
            if start and end and start <= end:
                return start, end
            # fallback to month if invalid custom range
        
        if period == 'quarter': 
            return today - timedelta(days=90), today
        elif period == 'year':
            start = today.replace(month=1, day=1)
            return start, today
        else:  # month to date (default)
            return today.replace(day=1), today
    
    @staticmethod
    def get_current_year_dates() -> Tuple[datetime.date, datetime.date]:
        """Get start and end dates for current year"""
        today = datetime.now().date()
        year_start = datetime(today.year, 1, 1).date()
        return year_start, today
    
    @staticmethod
    def get_current_month_dates() -> Tuple[datetime.date, datetime.date]:
        """Get start and end dates for current month"""
        today = datetime.now().date()
        month_start = today.replace(day=1)
        return month_start, today
    
    @staticmethod
    def days_left_in_month() -> int:
        """Get number of days left in current month"""
        today = datetime.now().date()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        return max(0, days_in_month - today.day)
    
    @staticmethod
    def days_left_in_year() -> int:
        """Get number of days left in current year"""
        today = datetime.now().date()
        year_end = datetime(today.year, 12, 31).date()
        return (year_end - today).days