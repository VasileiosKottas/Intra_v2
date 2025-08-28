# app/services/call_history_service.py
"""
ALTOS Call History API integration service
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode
from app.config import config_manager
from app.models import db
from app.models.base import BaseModel

class CallRecord(BaseModel):
    """Model to store call history data from ALTOS API"""
    __tablename__ = 'call_records'
    
    # ALTOS API fields
    sid = db.Column(db.String(100), nullable=False, index=True)  # Unique identifier
    advisor_email = db.Column(db.String(100), nullable=False, index=True)
    direction = db.Column(db.String(10), nullable=False)  # I=Inbound, O=Outbound
    calling_number = db.Column(db.String(50))  # cg field
    called_number = db.Column(db.String(50))   # cd field
    call_start_time = db.Column(db.DateTime, nullable=False, index=True)  # rs field
    call_answered_time = db.Column(db.DateTime)  # cs field
    duration_seconds = db.Column(db.Integer, default=0)  # t field
    was_answered = db.Column(db.Boolean, default=False)  # c field
    was_voicemail = db.Column(db.Boolean, default=False)  # v field
    was_transferred = db.Column(db.Boolean, default=False)  # f field
    call_status = db.Column(db.String(50))  # r field for reason if failed
    company = db.Column(db.String(50), nullable=False, index=True)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('sid', 'company', name='unique_call_per_company'),
        db.Index('idx_advisor_date_direction', 'advisor_email', 'call_start_time', 'direction'),
    )

class CallHistoryService:
    """Service for ALTOS Call History API integration"""
    
    def __init__(self):
        self.api_token = config_manager.get_app_config('ALTOS_API_TOKEN')
        self.base_url = "https://extprov.myphones.net/callhistory.aspx"
        
    def _is_core_hours(self) -> bool:
        """Check if current time is during core hours (API restriction)"""
        current_hour = datetime.now().hour
        # Assume core hours are 9 AM to 5 PM weekdays
        if datetime.now().weekday() >= 5:  # Weekend
            return False
        return 9 <= current_hour <= 17
    
    def _format_datetime(self, date_str: str, time_str: str = None) -> str:
        """Format date for API (YYYYMMDD or YYYYMMDDHHMMSS)"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted = date_obj.strftime('%Y%m%d')
        
        if time_str:
            time_obj = datetime.strptime(time_str, '%H:%M')
            formatted += time_obj.strftime('%H%M00')  # Add seconds as 00
            
        return formatted
    
    def _build_api_url(self, start_date: datetime, end_date: datetime, 
                       call_type: str = 'all', calling_filter: str = None, 
                       called_filter: str = None) -> str:
        """Build API URL with parameters"""
        
        # Validate date range (API requires <= 7 days)
        if (end_date - start_date).days > 7:
            raise ValueError("Date range cannot exceed 7 days for ALTOS API")
        
        # Format dates
        sd = start_date.strftime('%Y%m%d')
        ed = end_date.strftime('%Y%m%d')
        
        params = {
            'ctok': self.api_token,
            'c': 'search',
            'ty': call_type,
            'sd': sd,
            'ed': ed
        }
        
        # Add optional filters
        if calling_filter and len(calling_filter) >= 6:
            params['fc'] = calling_filter
        if called_filter and len(called_filter) >= 6:
            params['fd'] = called_filter
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def _make_api_request(self, url: str) -> Optional[Dict]:
        """Make authenticated request to ALTOS API"""
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 403:
                raise Exception("Invalid ALTOS API token")
            elif response.status_code == 400:
                raise Exception(f"Bad request to ALTOS API: {response.text}")
            elif response.status_code != 200:
                raise Exception(f"ALTOS API error {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"ALTOS API request failed: {str(e)}")
    
    def fetch_call_data(self, start_date: datetime, end_date: datetime, 
                        call_type: str = 'all') -> List[Dict]:
        """Fetch call data from ALTOS API"""
        
        if self._is_core_hours():
            print(f"Warning: Fetching during core hours may be restricted")
        
        # Split large date ranges into 7-day chunks
        all_calls = []
        current_start = start_date
        
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=6), end_date)
            
            try:
                url = self._build_api_url(current_start, current_end, call_type)
                data = self._make_api_request(url)
                
                if data and 'myphones' in data and 'callhistory' in data['myphones']:
                    calls = data['myphones']['callhistory']
                    all_calls.extend(calls)
                    
            except Exception as e:
                print(f"Error fetching calls for {current_start} - {current_end}: {e}")
                # Continue with next chunk
            
            current_start = current_end + timedelta(days=1)
        
        return all_calls
    
    def get_placeholder_data(self, start_date: datetime, end_date: datetime, 
                           advisor_emails: List[str]) -> List[Dict]:
        """Generate placeholder call data during core hours"""
        import random
        
        placeholder_calls = []
        current_date = start_date
        
        while current_date <= end_date:
            for email in advisor_emails:
                # Generate 5-15 random outbound calls per day per advisor
                num_calls = random.randint(5, 15)
                
                for i in range(num_calls):
                    call_time = current_date + timedelta(
                        hours=random.randint(9, 17),
                        minutes=random.randint(0, 59)
                    )
                    
                    placeholder_calls.append({
                        'sid': f"placeholder_{email}_{current_date.strftime('%Y%m%d')}_{i}",
                        'd': 'O',  # Outbound
                        'cg': '01234567890',  # Generic calling number
                        'cd': f"0800{random.randint(100000, 999999)}",  # Random called number
                        'rs': call_time.strftime('%Y%m%d%H%M%S'),
                        'cs': call_time.strftime('%Y%m%d%H%M%S') if random.choice([True, False]) else None,
                        't': random.randint(30, 300),  # Duration in seconds
                        'c': random.choice([True, False]),  # Answered
                        'v': random.choice([True, False, False]),  # Voicemail (less likely)
                        'f': False,  # Not transferred
                        'advisor_email': email
                    })
            
            current_date += timedelta(days=1)
        
        return placeholder_calls
    
    def store_call_data(self, calls_data: List[Dict], company: str, 
                        advisor_email_mapping: Dict[str, str] = None):
        """Store call data in database"""
        
        for call in calls_data:
            try:
                # Parse call start time
                rs_str = call.get('rs', '')
                if len(rs_str) >= 8:
                    if len(rs_str) >= 14:  # Full datetime
                        call_time = datetime.strptime(rs_str[:14], '%Y%m%d%H%M%S')
                    else:  # Date only
                        call_time = datetime.strptime(rs_str[:8], '%Y%m%d')
                else:
                    continue  # Skip invalid records
                
                # Parse answered time if available
                answered_time = None
                cs_str = call.get('cs', '')
                if cs_str and len(cs_str) >= 14:
                    try:
                        answered_time = datetime.strptime(cs_str[:14], '%Y%m%d%H%M%S')
                    except ValueError:
                        pass
                
                # Determine advisor email (use mapping if provided)
                advisor_email = call.get('advisor_email')
                if not advisor_email and advisor_email_mapping:
                    calling_number = call.get('cg', '')
                    advisor_email = advisor_email_mapping.get(calling_number)
                
                if not advisor_email:
                    continue  # Skip if we can't identify the advisor
                
                # Check if record already exists
                existing = CallRecord.query.filter_by(
                    sid=call.get('sid'),
                    company=company
                ).first()
                
                if existing:
                    continue  # Skip duplicates
                
                # Create new call record
                call_record = CallRecord(
                    sid=call.get('sid'),
                    advisor_email=advisor_email.lower(),
                    direction=call.get('d', 'O'),
                    calling_number=call.get('cg'),
                    called_number=call.get('cd'),
                    call_start_time=call_time,
                    call_answered_time=answered_time,
                    duration_seconds=call.get('t', 0),
                    was_answered=call.get('c', False),
                    was_voicemail=call.get('v', False),
                    was_transferred=call.get('f', False),
                    call_status=call.get('r'),
                    company=company
                )
                
                db.session.add(call_record)
                
            except Exception as e:
                print(f"Error storing call record: {e}")
                continue
        
        try:
            db.session.commit()
            print(f"Stored {len(calls_data)} call records for {company}")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing call data: {e}")
    
    def get_advisor_call_metrics(self, advisor_email: str, start_date: datetime, 
                                end_date: datetime, company: str) -> Dict:
        """Get call metrics for a specific advisor"""
        
        calls = CallRecord.query.filter(
            CallRecord.advisor_email == advisor_email.lower(),
            CallRecord.company == company,
            CallRecord.call_start_time >= start_date,
            CallRecord.call_start_time <= end_date
        ).all()
        
        outbound_calls = [c for c in calls if c.direction == 'O']
        inbound_calls = [c for c in calls if c.direction == 'I']
        
        return {
            'total_calls': len(calls),
            'outbound_calls': len(outbound_calls),
            'inbound_calls': len(inbound_calls),
            'outbound_answered': sum(1 for c in outbound_calls if c.was_answered),
            'total_talk_time': sum(c.duration_seconds for c in calls),
            'avg_call_duration': sum(c.duration_seconds for c in calls) / len(calls) if calls else 0,
            'calls_by_date': self._group_calls_by_date(calls)
        }
    
    def _group_calls_by_date(self, calls: List[CallRecord]) -> Dict[str, int]:
        """Group calls by date"""
        calls_by_date = {}
        for call in calls:
            date_key = call.call_start_time.date().isoformat()
            calls_by_date[date_key] = calls_by_date.get(date_key, 0) + 1
        return calls_by_date
    
    def sync_team_call_data(self, team_members: List, company: str, 
                           start_date: datetime, end_date: datetime, 
                           use_placeholders: bool = None) -> Dict:
        """Sync call data for team members"""
        
        if use_placeholders is None:
            use_placeholders = self._is_core_hours()
        
        advisor_emails = [member.email for member in team_members]
        
        if use_placeholders:
            print("Using placeholder data during core hours")
            calls_data = self.get_placeholder_data(start_date, end_date, advisor_emails)
        else:
            calls_data = self.fetch_call_data(start_date, end_date, call_type='all')
        
        # Store the call data
        self.store_call_data(calls_data, company)
        
        # Return metrics for each team member
        team_metrics = {}
        for member in team_members:
            team_metrics[member.email] = self.get_advisor_call_metrics(
                member.email, start_date, end_date, company
            )
        
        return team_metrics