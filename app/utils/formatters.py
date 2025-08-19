"""
Data formatting utilities
"""

from datetime import datetime, date
from typing import Union, Optional

def format_currency(amount: Union[int, float], currency_symbol: str = '£') -> str:
    """Format number as currency with proper thousands separators"""
    try:
        return f"{currency_symbol}{amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"

def format_date(date_obj: Union[datetime, date], format_string: str = '%d %b %Y') -> str:
    """Format date object to string"""
    try:
        if isinstance(date_obj, datetime):
            return date_obj.strftime(format_string)
        elif isinstance(date_obj, date):
            return date_obj.strftime(format_string)
        else:
            return str(date_obj)
    except (ValueError, AttributeError):
        return 'Invalid Date'

def format_percentage(value: Union[int, float], decimal_places: int = 1) -> str:
    """Format number as percentage"""
    try:
        return f"{value:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "0.0%"

def format_advisor_name(name: str) -> str:
    """Format advisor name consistently"""
    if not name:
        return 'Unknown Advisor'
    
    return name.title().strip()

def format_business_type(business_type: str) -> str:
    """Format business type for display"""
    if not business_type:
        return 'Unknown Type'
    
    # Handle special cases
    special_cases = {
        'btl': 'BTL',
        'gi': 'GI',
        'cnc': 'C&C'
    }
    
    formatted = business_type.strip()
    for abbrev, full in special_cases.items():
        formatted = formatted.replace(abbrev.lower(), full)
        formatted = formatted.replace(abbrev.upper(), full)
    
    return formatted