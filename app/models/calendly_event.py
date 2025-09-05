# app/models/calendly_event.py (FIXED VERSION)
"""
Calendly Event database model for caching Calendly API data - Fixed to handle data type issues
"""

from datetime import datetime
from app.models.base import BaseModel
from app.models import db
import json
import logging

logger = logging.getLogger(__name__)

class CalendlyEvent(BaseModel):
    """Model for storing Calendly events to reduce API calls"""
    
    __tablename__ = 'calendly_events'
    
    # Event identification
    calendly_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    calendly_uri = db.Column(db.String(500), nullable=False)
    
    # Event details
    name = db.Column(db.String(255))
    status = db.Column(db.String(50), index=True)  # active, completed, canceled
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Location and meeting details
    location_type = db.Column(db.String(100))
    location_value = db.Column(db.Text)
    meeting_notes_plain = db.Column(db.Text)
    meeting_notes_html = db.Column(db.Text)
    
    # Event type information
    event_type_name = db.Column(db.String(255))
    event_type_uri = db.Column(db.String(500))
    event_type_duration = db.Column(db.Integer)  # Duration in minutes
    
    # Host information
    host_name = db.Column(db.String(255), index=True)
    host_email = db.Column(db.String(255), index=True)
    host_uri = db.Column(db.String(500))
    
    # Guest information (JSON array of guests)
    guests_data = db.Column(db.JSON)  # Store array of guest objects
    guest_count = db.Column(db.Integer, default=0)
    
    # Timing and scheduling
    created_at_calendly = db.Column(db.DateTime)
    updated_at_calendly = db.Column(db.DateTime)
    
    # Booking and cancellation info
    cancel_url = db.Column(db.String(500))
    reschedule_url = db.Column(db.String(500))
    
    # Metadata
    raw_data = db.Column(db.JSON)  # Store full Calendly response for future reference
    last_synced = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<CalendlyEvent {self.calendly_event_id}: {self.name} at {self.start_time}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'calendly_event_id': self.calendly_event_id,
            'calendly_uri': self.calendly_uri,
            'name': self.name,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location_type': self.location_type,
            'location_value': self.location_value,
            'event_type_name': self.event_type_name,
            'event_type_duration': self.event_type_duration,
            'host_name': self.host_name,
            'host_email': self.host_email,
            'guests_data': self.guests_data,
            'guest_count': self.guest_count,
            'created_at_calendly': self.created_at_calendly.isoformat() if self.created_at_calendly else None,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None
        }
    
    @classmethod
    def create_from_calendly_data(cls, calendly_event_data):
        """Create CalendlyEvent instance from Calendly API response - FIXED to handle string data"""
        try:
            # FIXED: Handle case where data might be a string instead of dict
            if isinstance(calendly_event_data, str):
                logger.warning(f"Received string data instead of dict: {calendly_event_data[:100]}...")
                # Try to parse as JSON
                try:
                    calendly_event_data = json.loads(calendly_event_data)
                except json.JSONDecodeError:
                    logger.error(f"Cannot parse string data as JSON: {calendly_event_data}")
                    raise ValueError("Invalid event data format - expected dictionary")
            
            if not isinstance(calendly_event_data, dict):
                logger.error(f"Event data is not a dictionary: {type(calendly_event_data)}")
                raise ValueError(f"Invalid event data type: {type(calendly_event_data)}")
            
            # Extract event ID from URI
            calendly_uri = calendly_event_data.get('uri', '')
            calendly_event_id = calendly_uri.split('/')[-1] if calendly_uri else None
            
            if not calendly_event_id:
                logger.warning(f"No event ID found in data: {calendly_event_data}")
                raise ValueError("No event ID found in Calendly data")
            
            # Parse dates safely
            start_time = None
            end_time = None
            created_at = None
            updated_at = None
            
            try:
                if calendly_event_data.get('start_time'):
                    start_time = datetime.fromisoformat(calendly_event_data['start_time'].replace('Z', '+00:00')).replace(tzinfo=None)
                if calendly_event_data.get('end_time'):
                    end_time = datetime.fromisoformat(calendly_event_data['end_time'].replace('Z', '+00:00')).replace(tzinfo=None)
                if calendly_event_data.get('created_at'):
                    created_at = datetime.fromisoformat(calendly_event_data['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)
                if calendly_event_data.get('updated_at'):
                    updated_at = datetime.fromisoformat(calendly_event_data['updated_at'].replace('Z', '+00:00')).replace(tzinfo=None)
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing dates from event data: {e}")
                # Use current time as fallback
                if not start_time:
                    start_time = datetime.utcnow()
                if not end_time:
                    end_time = start_time
            
            # Extract location info safely
            location = calendly_event_data.get('location', {})
            location_type = None
            location_value = None
            
            if isinstance(location, dict):
                location_type = location.get('type')
                location_value = location.get('location')
            
            # Extract event type info safely
            event_type = calendly_event_data.get('event_type', {})
            event_type_name = None
            event_type_uri = None
            event_type_duration = None
            
            if isinstance(event_type, dict):
                event_type_name = event_type.get('name')
                event_type_uri = event_type.get('uri')
                event_type_duration = event_type.get('duration')
            
            # Extract host info from event_memberships safely
            host_name = None
            host_email = None
            host_uri = None
            guests_data = []
            
            event_memberships = calendly_event_data.get('event_memberships', [])
            if isinstance(event_memberships, list):
                for membership in event_memberships:
                    if isinstance(membership, dict):
                        user_name = membership.get('user_name')
                        user_email = membership.get('user_email')
                        user_uri = membership.get('user')
                        
                        if not host_name:  # Assume first membership is the host
                            host_name = user_name
                            host_email = user_email
                            host_uri = user_uri
                        else:  # Additional memberships are guests
                            guests_data.append({
                                'name': user_name,
                                'email': user_email,
                                'uri': user_uri
                            })
            
            return cls(
                calendly_event_id=calendly_event_id,
                calendly_uri=calendly_uri,
                name=calendly_event_data.get('name'),
                status=calendly_event_data.get('status'),
                start_time=start_time,
                end_time=end_time,
                location_type=location_type,
                location_value=location_value,
                meeting_notes_plain=calendly_event_data.get('meeting_notes_plain'),
                meeting_notes_html=calendly_event_data.get('meeting_notes_html'),
                event_type_name=event_type_name,
                event_type_uri=event_type_uri,
                event_type_duration=event_type_duration,
                host_name=host_name,
                host_email=host_email,
                host_uri=host_uri,
                guests_data=guests_data,
                guest_count=len(guests_data),
                created_at_calendly=created_at,
                updated_at_calendly=updated_at,
                cancel_url=calendly_event_data.get('cancel_url'),
                reschedule_url=calendly_event_data.get('reschedule_url'),
                raw_data=calendly_event_data,
                last_synced=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating CalendlyEvent from data: {e}")
            logger.error(f"Data type: {type(calendly_event_data)}")
            logger.error(f"Data preview: {str(calendly_event_data)[:200]}...")
            raise

class CalendlySyncLog(BaseModel):
    """Track Calendly sync operations to manage incremental updates"""
    
    __tablename__ = 'calendly_sync_logs'
    
    sync_type = db.Column(db.String(50), nullable=False)  # 'full', 'incremental', 'user_specific'
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime, nullable=False, index=True)
    
    # Sync results
    events_fetched = db.Column(db.Integer, default=0)
    events_created = db.Column(db.Integer, default=0)
    events_updated = db.Column(db.Integer, default=0)
    events_skipped = db.Column(db.Integer, default=0)
    
    # Status and timing
    status = db.Column(db.String(20), default='running')  # running, completed, failed
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    
    # Error handling
    error_message = db.Column(db.Text)
    api_calls_made = db.Column(db.Integer, default=0)
    
    # User/team specific syncs
    user_email = db.Column(db.String(255), index=True)  # If sync was for specific user
    team_id = db.Column(db.Integer, index=True)  # If sync was for specific team
    
    def __repr__(self):
        return f'<CalendlySyncLog {self.sync_type}: {self.start_date} to {self.end_date} - {self.status}>'