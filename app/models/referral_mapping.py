"""
Referral name mapping model for storing custom name mappings
"""

from app.models import db
from app.models.base import BaseModel

class ReferralMapping(BaseModel):
    """Model for storing referral name mappings"""
    __tablename__ = 'referral_mappings'
    
    referral_name = db.Column(db.String(100), nullable=False)  # e.g., "Steve/Protection"
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    advisor = db.relationship('Advisor', backref='referral_mappings')
    
    # Unique constraint to prevent duplicate mappings
    __table_args__ = (db.UniqueConstraint('referral_name', 'company', name='unique_referral_name_company'),)
    
    @classmethod
    def get_mappings_for_company(cls, company):
        """Get all active mappings for a company"""
        return cls.query.filter_by(company=company, is_active=True).all()
    
    @classmethod
    def get_advisor_for_referral(cls, referral_name, company):
        """Get advisor ID for a referral name in a company"""
        mapping = cls.query.filter_by(
            referral_name=referral_name.lower().strip(),
            company=company,
            is_active=True
        ).first()
        return mapping.advisor_id if mapping else None
    
    @classmethod
    def add_mapping(cls, referral_name, advisor_id, company):
        """Add or update a referral mapping"""
        referral_name_clean = referral_name.lower().strip()
        
        # Check if mapping already exists
        existing = cls.query.filter_by(
            referral_name=referral_name_clean,
            company=company
        ).first()
        
        if existing:
            existing.advisor_id = advisor_id
            existing.is_active = True
        else:
            new_mapping = cls(
                referral_name=referral_name_clean,
                advisor_id=advisor_id,
                company=company,
                is_active=True
            )
            db.session.add(new_mapping)
        
        db.session.commit()
        return True
    
    @classmethod
    def remove_mapping(cls, mapping_id):
        """Remove a referral mapping"""
        mapping = cls.query.get(mapping_id)
        if mapping:
            mapping.is_active = False
            db.session.commit()
            return True
        return False