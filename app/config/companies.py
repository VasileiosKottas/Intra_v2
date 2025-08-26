"""
Company-specific configurations and data
"""

from typing import Dict, List, Optional

class CompanyConfig:
    """Configuration for a specific company"""
    
    def __init__(self, name: str, logo: str, valid_business_types: List[str], 
                 valid_paid_case_types: List[str], advisor_names: List[str], 
                 name_mappings: Dict[str, str]):
        self.name = name
        self.logo = logo
        self.valid_business_types = valid_business_types
        self.valid_paid_case_types = valid_paid_case_types
        self.advisor_names = advisor_names
        self.name_mappings = name_mappings
    
    def is_valid_business_type(self, business_type: str) -> bool:
        """Check if business type is valid for this company"""
        return business_type in self.valid_business_types
    
    def is_valid_paid_case_type(self, case_type: str) -> bool:
        """Check if paid case type is valid for this company"""
        return case_type in self.valid_paid_case_types
    
    def normalize_advisor_name(self, name: str) -> Optional[str]:
        """Normalize advisor name using mappings"""
        if not name or name == "No Answer":
            return None
        
        name_clean = name.lower().strip()
        
        # Try exact mapping first
        if name_clean in self.name_mappings:
            return self.name_mappings[name_clean]
        
        # Try partial matching for complex names
        for key, standard_name in self.name_mappings.items():
            if key in name_clean or name_clean in key:
                return standard_name
        
        # If no mapping found, return cleaned version
        return name.title().strip()
    
    def is_valid_advisor(self, name: str) -> bool:
        """Check if advisor name is valid for this company"""
        normalized = self.normalize_advisor_name(name)
        return normalized in self.advisor_names if normalized else False

# Company data definitions
WINDSOR_CONFIG = CompanyConfig(
    name='Windsor',
    logo='White_and_teal_on_blue_2.png',
    valid_business_types=[
        'Residential Mortgage (Including BTL)',
        'Personal Insurance (Including GI)',
        'Product Transfer'
    ],
    valid_paid_case_types=[
        'Residential',
        'General Insurance',
        'Term insurance',
        'Other Referral'
    ],
    advisor_names=[
        'Daniel Jones', 'Drew Gibson', 'Elliot Cotterell',
        'Jamie Cope', 'Lottie Brown', 'Martyn Barberry', 'Michael Olivieri',
        'Oliver Cotterell', 'Rachel Ashworth', 'Steven Horn', 'Nick Snailum (Referral)',
        'Chris Bailey - Leaver', 'James Thomas - Leaver'
    ],
    name_mappings={
        'mike': 'Michael Olivieri',
        'michael': 'Michael Olivieri',
        'mike olivieri': 'Michael Olivieri',
        'michael olivieri': 'Michael Olivieri',
        'Michael Olivieri' : 'Michael Olivieri',
        'steve': 'Steven Horn',
        'steven': 'Steven Horn',
        'steve horn': 'Steven Horn',
        'steven horn': 'Steven Horn',
        'dan': 'Daniel Jones',
        'daniel': 'Daniel Jones',
        'dan jones': 'Daniel Jones',
        'daniel jones': 'Daniel Jones',
        'drew': 'Drew Gibson',
        'drew gibson': 'Drew Gibson',
        'jamie': 'Jamie Cope',
        'jamie cope': 'Jamie Cope',
        'oliver': 'Oliver Cotterell',
        'oliver cotterell': 'Oliver Cotterell',
        'elliot': 'Elliot Cotterell',
        'elliot cotterell': 'Elliot Cotterell',
        'rachel': 'Rachel Ashworth',
        'rachel ashworth': 'Rachel Ashworth',
        'lottie': 'Lottie Brown',
        'lottie brown': 'Lottie Brown',
        'martyn': 'Martyn Barberry',
        'martyn barberry': 'Martyn Barberry',
        'nick': 'Nick Snailum (Referral)',
        'nick snailum': 'Nick Snailum (Referral)',
        'chris': 'Chris Bailey - Leaver',
        'chris bailey': 'Chris Bailey - Leaver',
        'james': 'James Thomas - Leaver',
        'james thomas': 'James Thomas - Leaver',
    }
)

CNC_CONFIG = CompanyConfig(
    name='C&C',
    logo='CnC.png',
    valid_business_types=[
        'Bridging or Development',
        'Commercial',
        '2nd Charge - Regulated',
        '2nd Charge - Unregulated',
        'Development',
        'Business Loan'
    ],
    valid_paid_case_types=[
        'Bridging or Development',
        'Commercial',
        '2nd Charge - Regulated',
        '2nd Charge - Unregulated',
        'Development',
        'Business Loan'
    ],
    advisor_names=[
        'Daniel Jones', 'Drew Gibson', 'Elliot Cotterell',
        'Jamie Cope', 'Lottie Brown', 'Martyn Barberry', 'Michael Olivieri',
        'Oliver Cotterell', 'Rachel Ashworth', 'Steven Horn', 'Nick Snailum (Referral)',
        'Chris Bailey - Leaver', 'James Thomas - Leaver'
    ],
    name_mappings={
        'mike': 'Michael Olivieri',
        'michael': 'Michael Olivieri',
        'mike olivieri': 'Michael Olivieri',
        'michael olivieri': 'Michael Olivieri',
        'Michael Olivieri' : 'Michael Olivieri',
        'steve': 'Steven Horn',
        'steven': 'Steven Horn',
        'steve horn': 'Steven Horn',
        'steven horn': 'Steven Horn',
        'dan': 'Daniel Jones',
        'daniel': 'Daniel Jones',
        'dan jones': 'Daniel Jones',
        'daniel jones': 'Daniel Jones',
        'drew': 'Drew Gibson',
        'drew gibson': 'Drew Gibson',
        'jamie': 'Jamie Cope',
        'jamie cope': 'Jamie Cope',
        'oliver': 'Oliver Cotterell',
        'oliver cotterell': 'Oliver Cotterell',
        'elliot': 'Elliot Cotterell',
        'elliot cotterell': 'Elliot Cotterell',
        'rachel': 'Rachel Ashworth',
        'rachel ashworth': 'Rachel Ashworth',
        'lottie': 'Lottie Brown',
        'lottie brown': 'Lottie Brown',
        'martyn': 'Martyn Barberry',
        'martyn barberry': 'Martyn Barberry',
        'nick': 'Nick Snailum (Referral)',
        'nick snailum': 'Nick Snailum (Referral)',
        'chris': 'Chris Bailey - Leaver',
        'chris bailey': 'Chris Bailey - Leaver',
        'james': 'James Thomas - Leaver',
        'james thomas': 'James Thomas - Leaver',
    }
)