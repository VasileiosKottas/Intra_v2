"""
Referral recipient model for tracking who can receive referrals
"""


from app.models import db
from app.models.base import BaseModel

class ReferralRecipient(BaseModel):
    """Model for tracking advisors who can receive referrals"""
    __tablename__ = 'referral_recipients'
    
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    advisor = db.relationship('Advisor', backref='referral_settings')
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('advisor_id', 'company', name='unique_advisor_company_referral'),)
    
    @classmethod
    def get_recipients_for_company(cls, company):
        """Get all active referral recipients for a company"""
        return cls.query.filter_by(company=company, is_active=True).all()
    
    @classmethod
    def is_referral_recipient(cls, advisor_id, company):
        """Check if an advisor is a referral recipient for a company"""
        return cls.query.filter_by(
            advisor_id=advisor_id, 
            company=company, 
            is_active=True
        ).first() is not None
    
    @classmethod
    def set_referral_recipient(cls, advisor_id, company, is_active=True):
        """Set or update referral recipient status for an advisor"""
        existing = cls.query.filter_by(advisor_id=advisor_id, company=company).first()
        
        if existing:
            existing.is_active = is_active
        else:
            new_recipient = cls(
                advisor_id=advisor_id,
                company=company,
                is_active=is_active
            )
            db.session.add(new_recipient)
        
        db.session.commit()
        return True