"""
Sync log model
"""

from app.models import db
from app.models.base import BaseModel

class SyncLog(BaseModel):
    """Sync log model"""
    __tablename__ = 'sync_logs'
    
    sync_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    submissions_synced = db.Column(db.Integer, default=0)
    paid_cases_synced = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='success')
    error_message = db.Column(db.Text, nullable=True)
    company = db.Column(db.String(50), default='windsor')