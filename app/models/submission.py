# submission.py - Enhanced model to track original referral types

"""
Enhanced Submission model with original business type tracking
"""

from app.models import db
from app.models.base import BaseModel

class Submission(BaseModel):
    """Enhanced Submission model with original_business_type field"""
    __tablename__ = 'submissions'
    
    advisor_name = db.Column(db.String(100), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    business_type = db.Column(db.String(100), nullable=False)
    original_business_type = db.Column(db.String(100), nullable=True)  # NEW: Store original before filtering
    submission_date = db.Column(db.Date, nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    expected_proc = db.Column(db.Float, default=0)
    expected_fee = db.Column(db.Float, default=0)
    referral_to = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(50), default='windsor')
    jotform_id = db.Column(db.String(50), unique=True)

    @property
    def total_value(self):
        """Get total expected value"""
        return (self.expected_proc or 0) + (self.expected_fee or 0)
    
    def is_referral(self):
        """Check if this is a referral submission"""
        return self.business_type and self.business_type == 'Referral'
    
    def is_conveyancing_referral(self):
        """Check if this is a conveyancing referral (for YTD reports)"""
        if not self.is_referral():
            return False
        
        original = (self.original_business_type or '').lower()
        referral_to = (self.referral_to or '').lower()
        
        return any(keyword in original for keyword in ['conveyancing', 'conveyance']) or \
               any(keyword in referral_to for keyword in ['conveyancing', 'conveyance'])
    
    def is_survey_referral(self):
        """Check if this is a survey referral (for YTD reports)"""
        if not self.is_referral():
            return False
            
        original = (self.original_business_type or '').lower()
        referral_to = (self.referral_to or '').lower()
        
        return any(keyword in original for keyword in ['survey']) or \
               any(keyword in referral_to for keyword in ['survey'])
    
    def is_other_referral_for_ytd(self):
        """Check if this should count as 'Other Referrals' in YTD dashboard"""
        return self.is_conveyancing_referral() or self.is_survey_referral()