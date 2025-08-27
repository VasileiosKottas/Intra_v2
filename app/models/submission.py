"""
Submission model
"""

from app.models import db
from app.models.base import BaseModel

class Submission(BaseModel):
    """Submission model with income_type field"""
    __tablename__ = 'submissions'
    
    advisor_name = db.Column(db.String(100), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    business_type = db.Column(db.String(100), nullable=False)
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
        return self.business_type and self.business_type.startswith('Referral')
