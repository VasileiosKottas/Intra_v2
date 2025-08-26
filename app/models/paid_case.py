"""
Paid case model
"""

from app.models import db
from app.models.base import BaseModel

class PaidCase(BaseModel):
    """Paid case model with income_type field"""
    __tablename__ = 'paid_cases'
    
    advisor_name = db.Column(db.String(100), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    case_type = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    value = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.Date, nullable=False)
    company = db.Column(db.String(50), default='windsor')
    jotform_id = db.Column(db.String(50), unique=True)
    who_referred = db.Column(db.String(200), nullable=True)
    income_type = db.Column(db.String(100), nullable=True)  # NEW: Income type field
