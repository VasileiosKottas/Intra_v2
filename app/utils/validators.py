"""
Input validation helpers
"""

import re
from typing import Optional

def validate_email(email: str) -> bool:
    """Validate email address format"""
    if not email:
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format (UK format)"""
    if not phone:
        return False
    
    # Remove spaces, dashes, and parentheses
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # UK phone number patterns
    uk_patterns = [
        r'^(\+44|0044|44)?[1-9]\d{8,9}$',  # UK landline/mobile
        r'^(\+44|0044|44)?7\d{9}$',        # UK mobile specific
    ]
    
    return any(re.match(pattern, cleaned_phone) for pattern in uk_patterns)

def validate_currency(amount: str) -> tuple[bool, Optional[float]]:
    """Validate and parse currency amount"""
    if not amount:
        return False, None
    
    # Remove currency symbols and spaces
    cleaned_amount = re.sub(r'[£$€,\s]', '', str(amount))
    
    try:
        value = float(cleaned_amount)
        return value >= 0, value  # Non-negative amounts only
    except ValueError:
        return False, None

def validate_advisor_name(name: str, valid_names: list) -> bool:
    """Validate advisor name against list of valid names"""
    if not name or not valid_names:
        return False
    
    return name.strip() in valid_names

def validate_company(company: str) -> bool:
    """Validate company name"""
    valid_companies = ['windsor', 'cnc']
    return company.lower() in valid_companies
