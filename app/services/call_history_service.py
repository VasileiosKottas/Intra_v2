# Enhanced ALTOS Call History Service with Team Analytics
# app/services/call_history_service.py

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode
from app.config.settings import ConfigurationManager
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
    
    __table_args__ = (
        db.UniqueConstraint('sid', 'company', name='unique_call_per_company'),
        db.Index('idx_advisor_date_direction', 'advisor_email', 'call_start_time', 'direction'),
    )

class CallHistoryService:
    """Enhanced service for ALTOS Call History API integration with team analytics"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.api_token = self.config_manager.get_app_config('ALTOS_API_TOKEN')
        self.base_url = "https://extprov.myphones.net/callhistory.aspx"
        
    def _is_core_hours(self) -> bool:
        """Check if current time is during core hours (API restriction)"""
        current_hour = datetime.now().hour
        if datetime.now().weekday() >= 5:  # Weekend
            return False
        return 9 <= current_hour <= 17
    
    def _format_datetime(self, date_obj: datetime, include_time: bool = False) -> str:
        """Format datetime for API (YYYYMMDD or YYYYMMDDHHMMSS)"""
        formatted = date_obj.strftime('%Y%m%d')
        if include_time:
            formatted += date_obj.strftime('%H%M%S')
        return formatted
    
    def _build_api_url(self, start_date: datetime, end_date: datetime, 
                       call_type: str = 'outbound', calling_filter: str = None, 
                       called_filter: str = None) -> str:
        """Build API URL with parameters"""
        
        # Validate date range (API requires <= 7 days)
        if (end_date - start_date).days > 7:
            raise ValueError("Date range cannot exceed 7 days for ALTOS API")
        
        # Format dates
        sd = self._format_datetime(start_date)
        ed = self._format_datetime(end_date)
        
        params = {
            'ctok': self.api_token,
            'c': 'search',
            'ty': call_type,  # 'outbound', 'inbound', or 'all'
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
            print(f"ALTOS API Request: {url}")
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
                        call_type: str = 'outbound') -> List[Dict]:
        """Fetch call data from ALTOS API, handling date range limits"""
        
        if self._is_core_hours():
            print(f"Warning: Fetching during core hours may be restricted")
        
        # Split large date ranges into 7-day chunks
        all_calls = []
        current_start = start_date
        
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=6), end_date)
            
            try:
                url = self._build_api_url(current_start, current_end, call_type)
                data = self._make_api_request(url)
                
                if data and 'myphones' in data and 'callhistory' in data['myphones']:
                    calls = data['myphones']['callhistory']
                    
                    # Ensure calls is a list
                    if isinstance(calls, dict):
                        calls = [calls]  # Single call returned as dict
                    elif not isinstance(calls, list):
                        calls = []
                    
                    all_calls.extend(calls)
                    print(f"Fetched {len(calls)} calls for {current_start.date()} - {current_end.date()}")
                else:
                    print(f"No call data returned for {current_start.date()} - {current_end.date()}")
                    
            except Exception as e:
                print(f"Error fetching calls for {current_start.date()} - {current_end.date()}: {e}")
                # Continue with next chunk rather than failing completely
         
            # Move to next chunk
            current_start = current_end + timedelta(days=1)
        
        print(f"Total calls fetched: {len(all_calls)}")
        return all_calls
    
    def get_team_call_analytics(self, team_members: List, start_date: datetime, 
                               end_date: datetime, company: str) -> Dict:
        """Get call analytics for entire team"""
        analytics = {}
        
        try:
            # Fetch all call data for the period
            outbound_calls = self.fetch_call_data(start_date, end_date, 'outbound')
            inbound_calls = self.fetch_call_data(start_date, end_date, 'inbound')
            
            # Process each team member
            for member in team_members:
                member_email = self._get_member_email(member)
                
                # Filter calls for this member
                member_outbound = [call for call in outbound_calls 
                                 if call.get('advisor_email', '').lower() == member_email.lower()]
                member_inbound = [call for call in inbound_calls 
                                if call.get('advisor_email', '').lower() == member_email.lower()]
                
                # Calculate statistics
                analytics[member_email] = {
                    'outbound_calls': len(member_outbound),
                    'inbound_calls': len(member_inbound),
                    'total_calls': len(member_outbound) + len(member_inbound),
                    'answered_outbound': len([c for c in member_outbound if c.get('was_answered', False)]),
                    'answered_inbound': len([c for c in member_inbound if c.get('was_answered', False)]),
                    'total_duration': sum(c.get('duration_seconds', 0) for c in member_outbound + member_inbound),
                    'avg_call_duration': 0
                }
                
                # Calculate average call duration
                total_answered = analytics[member_email]['answered_outbound'] + analytics[member_email]['answered_inbound']
                if total_answered > 0:
                    analytics[member_email]['avg_call_duration'] = analytics[member_email]['total_duration'] / total_answered

        except Exception as e:
            print(f"Error getting team call analytics: {e}")
            # Return empty analytics for all members on error
            for member in team_members:
                member_email = self._get_member_email(member)
                analytics[member_email] = {
                    'outbound_calls': 0, 'inbound_calls': 0, 'total_calls': 0,
                    'answered_outbound': 0, 'answered_inbound': 0, 'total_duration': 0,
                    'avg_call_duration': 0
                }
        
        return analytics
    
    def _get_member_email(self, member) -> str:
        """Get member email with fallback"""
        if hasattr(member, 'email') and member.email:
            return member.email
        
        # Generate email from name as fallback
        return f"{member.full_name.lower().replace(' ', '.')}@company.com"
    
    def sync_call_records_to_db(self, calls_data: List[Dict], company: str) -> int:
        """Sync call records to database to avoid repeated API calls"""
        synced_count = 0
        
        try:
            for call in calls_data:
                # Check if record already exists
                existing = CallRecord.query.filter_by(
                    sid=call.get('sid'),
                    company=company
                ).first()
                
                if not existing:
                    # Parse datetime fields
                    start_time = self._parse_altos_datetime(call.get('rs'))
                    answered_time = self._parse_altos_datetime(call.get('cs')) if call.get('cs') else None
                    
                    # Create new record
                    record = CallRecord(
                        sid=call.get('sid'),
                        advisor_email=call.get('advisor_email', ''),
                        direction=call.get('direction', 'O'),
                        calling_number=call.get('cg'),
                        called_number=call.get('cd'),
                        call_start_time=start_time,
                        call_answered_time=answered_time,
                        duration_seconds=int(call.get('t', 0)),
                        was_answered=bool(call.get('c', False)),
                        was_voicemail=bool(call.get('v', False)),
                        was_transferred=bool(call.get('f', False)),
                        call_status=call.get('r', ''),
                        company=company
                    )
                    
                    db.session.add(record)
                    synced_count += 1
            
            db.session.commit()
            print(f"Synced {synced_count} new call records to database")
            
        except Exception as e:
            print(f"Error syncing call records: {e}")
            db.session.rollback()
        
        return synced_count
    
    def _parse_altos_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse ALTOS datetime string to Python datetime"""
        if not datetime_str:
            return None
        
        try:
            # ALTOS returns datetime in format: YYYYMMDDHHMMSS
            if len(datetime_str) >= 14:
                return datetime.strptime(datetime_str[:14], '%Y%m%d%H%M%S')
            elif len(datetime_str) >= 8:
                return datetime.strptime(datetime_str[:8], '%Y%m%d')
            else:
                return None
        except ValueError as e:
            print(f"Error parsing ALTOS datetime '{datetime_str}': {e}")
            return None
    
    def get_cached_call_data(self, start_date: datetime, end_date: datetime, 
                           company: str, call_type: str = 'outbound') -> List[Dict]:
        """Get call data from database cache first, then API if needed"""
        try:
            # Check if we have recent data in cache
            cached_records = CallRecord.query.filter(
                CallRecord.company == company,
                CallRecord.call_start_time >= start_date,
                CallRecord.call_start_time <= end_date,
                CallRecord.direction == ('O' if call_type == 'outbound' else 'I')
            ).all()
            
            # If we have recent cached data (within last 2 hours), use it
            if cached_records:
                latest_record = max(cached_records, key=lambda x: x.created_at)
                cache_age = datetime.utcnow() - latest_record.created_at
                
                if cache_age.total_seconds() < 7200:  # 2 hours
                    print(f"Using cached call data ({len(cached_records)} records)")
                    return [self._record_to_dict(record) for record in cached_records]
            
            # Fetch fresh data from API
            print("Fetching fresh call data from ALTOS API...")
            fresh_data = self.fetch_call_data(start_date, end_date, call_type)
            
            # Cache the fresh data
            if fresh_data:
                self.sync_call_records_to_db(fresh_data, company)
            
            return fresh_data
            
        except Exception as e:
            print(f"Error getting call data: {e}")
            # Fallback to cached data even if old
            cached_records = CallRecord.query.filter(
                CallRecord.company == company,
                CallRecord.call_start_time >= start_date,
                CallRecord.call_start_time <= end_date
            ).all()
            
            return [self._record_to_dict(record) for record in cached_records]
    
    def _record_to_dict(self, record: CallRecord) -> Dict:
        """Convert CallRecord to dictionary matching API format"""
        return {
            'sid': record.sid,
            'advisor_email': record.advisor_email,
            'direction': record.direction,
            'cg': record.calling_number,
            'cd': record.called_number,
            'rs': record.call_start_time.strftime('%Y%m%d%H%M%S') if record.call_start_time else '',
            'cs': record.call_answered_time.strftime('%Y%m%d%H%M%S') if record.call_answered_time else '',
            't': record.duration_seconds,
            'c': record.was_answered,
            'v': record.was_voicemail,
            'f': record.was_transferred,
            'r': record.call_status
        }
    
    def get_team_analytics_summary(self, team_members: List, start_date: datetime, 
                                  end_date: datetime, company: str) -> Dict:
        """Get comprehensive call analytics for a team"""
        analytics = {
            'team_totals': {
                'total_outbound': 0,
                'total_inbound': 0,
                'answered_outbound': 0,
                'answered_inbound': 0,
                'total_duration': 0
            },
            'member_breakdown': {}
        }
        
        try:
            # Get call data (using cache when possible)
            outbound_calls = self.get_cached_call_data(start_date, end_date, company, 'outbound')
            inbound_calls = self.get_cached_call_data(start_date, end_date, company, 'inbound')
            
            # Process each team member
            for member in team_members:
                member_email = self._get_member_email(member).lower()
                
                # Filter calls for this member
                member_outbound = [call for call in outbound_calls 
                                 if call.get('advisor_email', '').lower() == member_email]
                member_inbound = [call for call in inbound_calls 
                                if call.get('advisor_email', '').lower() == member_email]
                
                # Calculate member statistics
                member_stats = {
                    'outbound_calls': len(member_outbound),
                    'inbound_calls': len(member_inbound),
                    'total_calls': len(member_outbound) + len(member_inbound),
                    'answered_outbound': len([c for c in member_outbound if c.get('c', False)]),
                    'answered_inbound': len([c for c in member_inbound if c.get('c', False)]),
                    'total_duration': sum(c.get('t', 0) for c in member_outbound + member_inbound),
                    'avg_call_duration': 0,
                    'voicemails': len([c for c in member_outbound + member_inbound if c.get('v', False)]),
                    'success_rate': 0
                }
                
                # Calculate averages and rates
                total_answered = member_stats['answered_outbound'] + member_stats['answered_inbound']
                if total_answered > 0:
                    member_stats['avg_call_duration'] = member_stats['total_duration'] / total_answered
                
                if member_stats['outbound_calls'] > 0:
                    member_stats['success_rate'] = (member_stats['answered_outbound'] / member_stats['outbound_calls']) * 100
                
                analytics['member_breakdown'][member_email] = member_stats
                
                # Add to team totals
                analytics['team_totals']['total_outbound'] += member_stats['outbound_calls']
                analytics['team_totals']['total_inbound'] += member_stats['inbound_calls'] 
                analytics['team_totals']['answered_outbound'] += member_stats['answered_outbound']
                analytics['team_totals']['answered_inbound'] += member_stats['answered_inbound']
                analytics['team_totals']['total_duration'] += member_stats['total_duration']
        
        except Exception as e:
            print(f"Error getting team call analytics: {e}")
            # Return empty analytics for all members on error
            for member in team_members:
                member_email = self._get_member_email(member)
                analytics['member_breakdown'][member_email] = {
                    'outbound_calls': 0, 'inbound_calls': 0, 'total_calls': 0,
                    'answered_outbound': 0, 'answered_inbound': 0, 'total_duration': 0,
                    'avg_call_duration': 0, 'voicemails': 0, 'success_rate': 0
                }
        
        return analytics
    
    def _get_member_email(self, member) -> str:
        """Get member email with fallback"""
        if hasattr(member, 'email') and member.email:
            return member.email
        
        # Generate email from name as fallback
        return f"{member.full_name.lower().replace(' ', '.')}@company.com"
    
    def test_api_connection(self) -> Dict:
        """Test ALTOS API connection"""
        try:
            if not self.api_token:
                return {'success': False, 'error': 'No ALTOS API token configured'}
            
            # Test with yesterday's data (small range)
            yesterday = datetime.now() - timedelta(days=1)
            test_url = self._build_api_url(yesterday, yesterday, 'outbound')
            
            data = self._make_api_request(test_url)
            
            if data:
                call_count = 0
                if 'myphones' in data and 'callhistory' in data['myphones']:
                    calls = data['myphones']['callhistory']
                    if isinstance(calls, list):
                        call_count = len(calls)
                    elif isinstance(calls, dict):
                        call_count = 1
                
                return {
                    'success': True, 
                    'message': f'API connection successful, found {call_count} calls for yesterday',
                    'test_date': yesterday.strftime('%Y-%m-%d')
                }
            else:
                return {'success': False, 'error': 'No data returned from API'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_member_call_summary(self, member_email: str, start_date: datetime, 
                               end_date: datetime, company: str) -> Dict:
        """Get detailed call summary for a specific member"""
        try:
            # Get cached data first
            outbound_calls = self.get_cached_call_data(start_date, end_date, company, 'outbound')
            inbound_calls = self.get_cached_call_data(start_date, end_date, company, 'inbound')
            
            # Filter for this member
            member_outbound = [call for call in outbound_calls 
                             if call.get('advisor_email', '').lower() == member_email.lower()]
            member_inbound = [call for call in inbound_calls 
                            if call.get('advisor_email', '').lower() == member_email.lower()]
            
            return {
                'outbound_calls': len(member_outbound),
                'inbound_calls': len(member_inbound),
                'outbound_details': member_outbound,
                'inbound_details': member_inbound,
                'summary': {
                    'total_calls': len(member_outbound) + len(member_inbound),
                    'answered_calls': len([c for c in member_outbound + member_inbound if c.get('c', False)]),
                    'total_duration_minutes': sum(c.get('t', 0) for c in member_outbound + member_inbound) / 60,
                    'success_rate': (len([c for c in member_outbound if c.get('c', False)]) / len(member_outbound) * 100) if member_outbound else 0
                }
            }
            
        except Exception as e:
            print(f"Error getting member call summary for {member_email}: {e}")
            return {
                'outbound_calls': 0, 'inbound_calls': 0,
                'outbound_details': [], 'inbound_details': [],
                'summary': {'total_calls': 0, 'answered_calls': 0, 'total_duration_minutes': 0, 'success_rate': 0}
            }