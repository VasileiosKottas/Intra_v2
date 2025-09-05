# app/models/__init__.py
"""
Database models package
Exports all models and database instance
Updated to include Calendly cache models
"""

from flask_sqlalchemy import SQLAlchemy

# Global database instance
db = SQLAlchemy()

def init_db(app):
    """Initialize database with app"""
    db.init_app(app)

# Import all models
from .advisor import Advisor, AdvisorGoal
from .team import Team, AdvisorTeam
from .submission import Submission
from .paid_case import PaidCase
from .sync_log import SyncLog
from .referral_recipient import ReferralRecipient
from .referral_mapping import ReferralMapping

# Import new Calendly cache models
from .calendly_event import CalendlyEvent, CalendlySyncLog

__all__ = [
    'db', 'init_db',
    'Advisor', 'AdvisorGoal', 'Team', 'AdvisorTeam', 
    'Submission', 'PaidCase', 'SyncLog', 'ReferralRecipient',
    'ReferralMapping', 'CalendlyEvent', 'CalendlySyncLog'
]