# app/services/calendly_service.py
"""
Calendly API integration service using Personal Access Token
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import config_manager
from typing import Dict, List, Optional

class CalendlyService:
    """Service for Calendly API integration with Personal Access Token"""
    
    def __init__(self):
        self.access_token = config_manager.get_app_config('CALENDLY_ACCESS_TOKEN')
        self.base_url = "https://api.calendly.com"
        self.user_uri = None  # Will be populated after first API call
        
    def _make_api_request(self, endpoint: str, method: str = 'GET', 
                         params: Optional[Dict] = None,
                         data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Calendly API"""
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Calendly API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
    
    def get_user_info(self) -> Optional[Dict]:
        """Get current user information"""
        user_data = self._make_api_request('/users/me')
        if user_data and 'resource' in user_data:
            self.user_uri = user_data['resource']['uri']
        return user_data
    
    def get_event_types(self) -> Optional[Dict]:
        """Get user's event types"""
        if not self.user_uri:
            user_info = self.get_user_info()
            if not user_info:
                return None
        
        params = {'user': self.user_uri}
        return self._make_api_request('/event_types', params=params)
    
    def get_scheduled_events(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        count: int = 100,
        event_type_uri: Optional[str] = None,
        user_uri: Optional[str] = None,
        status: Optional[str] = None  # 'active' | 'canceled' etc.
    ) -> Optional[Dict]:
        if not self.user_uri:
            user_info = self.get_user_info()
            if not user_info:
                return None

        params = {
            'user': user_uri or self.user_uri,      # allow override per user
            'count': min(count, 100)
        }
        if start_time:
            params['min_start_time'] = start_time.isoformat()
        if end_time:
            params['max_start_time'] = end_time.isoformat()
        if event_type_uri:
            params['event_type'] = event_type_uri
        if status:
            params['status'] = status

        return self._make_api_request('/scheduled_events', params=params)
    
    def get_event_invitees(self, event_uuid: str) -> Optional[Dict]:
        """Get invitee information for a specific event"""
        endpoint = f'/scheduled_events/{event_uuid}/invitees'
        return self._make_api_request(endpoint)
    
    def get_organization_memberships(self) -> Optional[Dict]:
        """Get organization memberships"""
        if not self.user_uri:
            user_info = self.get_user_info()
            if not user_info:
                return None
        
        params = {'user': self.user_uri}
        return self._make_api_request('/organization_memberships', params=params)
    
    def get_webhooks(self) -> Optional[Dict]:
        """Get webhook subscriptions"""
        # First get organization
        org_memberships = self.get_organization_memberships()
        if not org_memberships or not org_memberships.get('collection'):
            return None
        
        # Use first organization
        org_uri = org_memberships['collection'][0]['organization']
        params = {'organization': org_uri, 'scope': 'user'}
        return self._make_api_request('/webhook_subscriptions', params=params)
    
    def create_webhook(self, callback_url: str, events: List[str]) -> Optional[Dict]:
        """Create a webhook subscription"""
        org_memberships = self.get_organization_memberships()
        if not org_memberships or not org_memberships.get('collection'):
            return None
        
        org_uri = org_memberships['collection'][0]['organization']
        
        data = {
            'url': callback_url,
            'events': events,
            'organization': org_uri,
            'scope': 'user',
            'user': self.user_uri
        }
        
        return self._make_api_request('/webhook_subscriptions', method='POST', data=data)
    
    def test_connection(self) -> bool:
        """Test if the API connection is working"""
        user_info = self.get_user_info()
        return user_info is not None and 'resource' in user_info
    
    def get_analytics_data(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get analytics data for dashboard integration"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        events_data = self.get_scheduled_events(start_date, end_date)
        
        if not events_data or 'collection' not in events_data:
            return {
                'total_meetings': 0,
                'meetings_this_week': 0,
                'meetings_this_month': 0,
                'upcoming_meetings': 0,
                'events': []
            }
        
        events = events_data['collection']
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Process events
        total_meetings = len(events)
        meetings_this_week = 0
        meetings_this_month = 0
        upcoming_meetings = 0
        processed_events = []
        
        for event in events:
            start_time_str = event.get('start_time', '')
            if start_time_str:
                try:
                    event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    event_time = event_time.replace(tzinfo=None)  # Remove timezone for comparison
                    
                    # Count metrics
                    if event_time >= week_ago:
                        meetings_this_week += 1
                    if event_time >= month_ago:
                        meetings_this_month += 1
                    if event_time >= now:
                        upcoming_meetings += 1
                    
                    # Process event data
                    processed_events.append({
                        'uuid': event.get('uuid'),
                        'name': event.get('name'),
                        'start_time': event_time,
                        'end_time': datetime.fromisoformat(event.get('end_time', '').replace('Z', '+00:00')).replace(tzinfo=None) if event.get('end_time') else None,
                        'status': event.get('status'),
                        'event_type': event.get('event_type'),
                        'location': event.get('location', {})
                    })
                    
                except (ValueError, TypeError) as e:
                    print(f"Error parsing event time: {e}")
                    continue
        
    def get_organization_users(self) -> Optional[Dict]:
        """Get all users in the organization"""
        org_memberships = self.get_organization_memberships()
        if not org_memberships or not org_memberships.get('collection'):
            return None
        
        org_uri = org_memberships['collection'][0]['organization']
        params = {'organization': org_uri}
        return self._make_api_request('/organization_memberships', params=params)
    
    def get_analytics_data_by_user(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get analytics data broken down by user"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get organization users first
        org_users = self.get_organization_users()
        if not org_users or 'collection' not in org_users:
            return {'error': 'Could not fetch organization users'}
        
        users_data = {}
        total_events = 0
        
        # Get events for each user
        for membership in org_users['collection']:
            user_info = membership.get('user')
            if not user_info:
                continue
                
            user_uri = user_info.get('uri')
            user_name = user_info.get('name', 'Unknown User')
            user_email = user_info.get('email', '')
            
            if not user_uri:
                continue
            
            # Get events for this specific user
            user_events = self.get_scheduled_events(
                start_date, end_date, count=100, user_uri=user_uri
            )
            # Filter events for this user (events are already filtered by the user_uri in get_scheduled_events)
            user_event_count = 0
            user_events_list = []
            
            if user_events and 'collection' in user_events:
                events = user_events['collection']
                user_event_count = len(events)
                total_events += user_event_count
                
                for event in events:
                    start_time_str = event.get('start_time', '')
                    if start_time_str:
                        try:
                            event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                            event_time = event_time.replace(tzinfo=None)
                            
                            user_events_list.append({
                                'name': event.get('name'),
                                'start_time': event_time.isoformat(),
                                'status': event.get('status'),
                                'uuid': event.get('uuid')
                            })
                        except (ValueError, TypeError):
                            continue
            
            users_data[user_uri] = {
                'name': user_name,
                'email': user_email,
                'events_count': user_event_count,
                'events': sorted(user_events_list, key=lambda x: x['start_time'])
            }
        
        return {
            'total_events': total_events,
            'users': users_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_team_events_analysis(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get detailed events analysis suitable for team reporting"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        events_data = self.get_scheduled_events(start_date, end_date)
        
        if not events_data or 'collection' not in events_data:
            return {
                'total_events': 0,
                'events_by_day': {},
                'events_by_type': {},
                'events_by_status': {},
                'events_by_hour': {},
                'upcoming_events': 0,
                'past_events': 0,
                'detailed_events': []
            }
        
        events = events_data['collection']
        now = datetime.now()
        
        # Initialize analysis containers
        events_by_day = {}
        events_by_type = {}
        events_by_status = {}
        events_by_hour = {}
        upcoming_events = 0
        past_events = 0
        detailed_events = []
        
        for event in events:
            start_time_str = event.get('start_time', '')
            if not start_time_str:
                continue
                
            try:
                event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                event_time = event_time.replace(tzinfo=None)  # Remove timezone for comparison
                
                # Count by day
                day_key = event_time.date().isoformat()
                events_by_day[day_key] = events_by_day.get(day_key, 0) + 1
                
                # Count by event type
                event_type_name = event.get('event_type', 'Unknown')
                events_by_type[event_type_name] = events_by_type.get(event_type_name, 0) + 1
                
                # Count by status
                status = event.get('status', 'unknown')
                events_by_status[status] = events_by_status.get(status, 0) + 1
                
                # Count by hour
                hour = event_time.hour
                events_by_hour[hour] = events_by_hour.get(hour, 0) + 1
                
                # Count upcoming vs past
                if event_time >= now:
                    upcoming_events += 1
                else:
                    past_events += 1
                
                # Get invitee data if needed
                invitees_data = None
                event_uuid = event.get('uuid')
                if event_uuid:
                    invitees_data = self.get_event_invitees(event_uuid)
                
                # Add detailed event info
                detailed_events.append({
                    'uuid': event.get('uuid'),
                    'name': event.get('name'),
                    'start_time': event_time,
                    'end_time': datetime.fromisoformat(event.get('end_time', '').replace('Z', '+00:00')).replace(tzinfo=None) if event.get('end_time') else None,
                    'status': event.get('status'),
                    'event_type': event.get('event_type'),
                    'location': event.get('location', {}),
                    'invitees_count': len(invitees_data.get('collection', [])) if invitees_data else 0,
                    'is_upcoming': event_time >= now
                })
                
            except (ValueError, TypeError) as e:
                print(f"Error parsing event time: {e}")
                continue
        
        return {
            'total_events': len(events),
            'events_by_day': dict(sorted(events_by_day.items())),
            'events_by_type': events_by_type,
            'events_by_status': events_by_status,
            'events_by_hour': dict(sorted(events_by_hour.items(), key=lambda x: int(x[0]))),
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'detailed_events': sorted(detailed_events, key=lambda x: x['start_time']),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    def get_organization_scheduled_events(self, start_time: datetime = None, 
                                            end_time: datetime = None, 
                                            count: int = 100) -> Optional[Dict]:
            """Get ALL scheduled events across the organization"""
            
            # First get organization info
            org_memberships = self.get_organization_memberships()
            if not org_memberships or 'collection' not in org_memberships:
                return None
            
            # Use organization URI instead of user URI
            org_uri = org_memberships['collection'][0]['organization']
            
            params = {
                'organization': org_uri,  # This gets ALL events in the organization
                'count': min(count, 100)
            }
            
            if start_time:
                params['min_start_time'] = start_time.isoformat()
            
            if end_time:
                params['max_start_time'] = end_time.isoformat()
                
            return self._make_api_request('/scheduled_events', params=params)

    def get_host_analytics_data(self, host_emails: List[str], 
                               start_date: datetime = None, 
                               end_date: datetime = None) -> Dict:
        """Get analytics data for specific hosts by their email addresses"""
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get ALL organization events
        events_data = self.get_organization_scheduled_events(start_date, end_date, count=500)
        
        if not events_data or 'collection' not in events_data:
            return {'error': 'Could not fetch organization events'}
        
        # Process events and group by host
        host_analytics = {}
        total_events = 0
        
        # Initialize host data
        for email in host_emails:
            host_analytics[email.lower()] = {
                'events_count': 0,
                'events': [],
                'events_by_status': {'active': 0, 'canceled': 0},
                'events_by_type': {}
            }
        
        for event in events_data['collection']:
            # Get event memberships to find the host
            event_memberships = event.get('event_memberships', [])
            
            for membership in event_memberships:
                member_email = membership.get('user_email', '').lower()
                
                # Check if this member is one of our target hosts
                if member_email in [email.lower() for email in host_emails]:
                    start_time_str = event.get('start_time', '')
                    status = event.get('status', 'unknown')
                    
                    try:
                        event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        event_time = event_time.replace(tzinfo=None)
                        
                        event_data = {
                            'name': event.get('name'),
                            'start_time': event_time.isoformat(),
                            'status': status,
                            'uri': event.get('uri'),
                            'event_type': event.get('event_type', ''),
                            'location': event.get('location', {}),
                            'participant_count': len(event_memberships)
                        }
                        
                        host_analytics[member_email]['events'].append(event_data)
                        host_analytics[member_email]['events_count'] += 1
                        host_analytics[member_email]['events_by_status'][status] = \
                            host_analytics[member_email]['events_by_status'].get(status, 0) + 1
                        
                        # Count by event type name (extract from URI)
                        event_type_name = event.get('name', 'Unknown Event')
                        host_analytics[member_email]['events_by_type'][event_type_name] = \
                            host_analytics[member_email]['events_by_type'].get(event_type_name, 0) + 1
                        
                        total_events += 1
                        
                    except (ValueError, TypeError):
                        continue
        
        # Sort events by start time for each host
        for email in host_analytics:
            host_analytics[email]['events'].sort(key=lambda x: x['start_time'])
        
        return {
            'total_events': total_events,
            'hosts': host_analytics,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

    def get_user_by_email(self, email: str) -> Optional[str]:
        """Get user URI by email address"""
        org_users = self.get_organization_users()
        if not org_users or 'collection' not in org_users:
            return None
            
        for membership in org_users['collection']:
            user_info = membership.get('user', {})
            if user_info.get('email', '').lower() == email.lower():
                return user_info.get('uri')
        return None
    
    def get_events_for_user(self, user_uri: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get all events for a specific user (where they are the host/owner)"""
        
        # Get organization URI first
        org_memberships = self.get_organization_memberships()
        if not org_memberships or 'collection' not in org_memberships:
            return []
        org_uri = org_memberships['collection'][0]['organization']
        
        params = {
            'user': user_uri,
            'organization': org_uri,  # Required for organization users
            'count': 100,
            'min_start_time': start_date.isoformat(),
            'max_start_time': end_date.isoformat()
        }
        
        all_events = []
        page_token = None
        
        while True:
            if page_token:
                params['page_token'] = page_token
                
            response = self._make_api_request('/scheduled_events', params=params)
            
            if not response or 'collection' not in response:
                break
                
            events = response['collection']
            all_events.extend(events)
            
            # Check pagination
            pagination = response.get('pagination', {})
            if not pagination.get('has_next_page'):
                break
                
            page_token = pagination.get('next_page_token')
            if not page_token:
                break
        
        return all_events
    
    def get_correct_host_analytics_data(self, host_emails: List[str], 
                                    start_date: datetime = None, 
                                    end_date: datetime = None) -> Dict:
        """Get analytics data for hosts based on their event ownership (not participation)"""
        
        # Default to last 60 days
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=60)
            print(start_date, end_date)
        print(f"Fetching host analytics from {start_date.date()} to {end_date.date()}")
        
        host_analytics = {}
        total_events = 0
        
        # Initialize host data
        for email in host_emails:
            host_analytics[email.lower()] = {
                'events_count': 0,
                'events': [],
                'events_by_status': {'active': 0, 'canceled': 0},
                'events_by_type': {},
                'user_uri': None,
                'user_found': False
            }
        
        # For each host, get their user URI and then their events
        for email in host_emails:
            print(f"Processing host: {email}")
            
            # Get user URI for this email
            user_uri = self.get_user_by_email(email)
            if not user_uri:
                print(f"Could not find user URI for {email}")
                continue
                
            host_analytics[email.lower()]['user_uri'] = user_uri
            host_analytics[email.lower()]['user_found'] = True
            
            # Get all events for this user (where they are the host)
            user_events = self.get_events_for_user(user_uri, start_date, end_date)
            print(f"Found {len(user_events)} events for {email}")
            
            for event in user_events:
                start_time_str = event.get('start_time', '')
                status = event.get('status', 'unknown')
                
                try:
                    event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    event_time = event_time.replace(tzinfo=None)
                    
                    # Only count past events (completed ones)
                    if event_time > datetime.now():
                        continue
                        
                    event_data = {
                        'name': event.get('name'),
                        'start_time': event_time.isoformat(),
                        'status': status,
                        'uri': event.get('uri'),
                        'event_type': event.get('event_type', ''),
                        'location': event.get('location', {}),
                        'invitees_counter': event.get('invitees_counter', {})
                    }
                    
                    host_analytics[email.lower()]['events'].append(event_data)
                    host_analytics[email.lower()]['events_count'] += 1
                    host_analytics[email.lower()]['events_by_status'][status] = \
                        host_analytics[email.lower()]['events_by_status'].get(status, 0) + 1
                    
                    # Count by event type name
                    event_type_name = event.get('name', 'Unknown Event')
                    host_analytics[email.lower()]['events_by_type'][event_type_name] = \
                        host_analytics[email.lower()]['events_by_type'].get(event_type_name, 0) + 1
                    
                    total_events += 1
                    
                except (ValueError, TypeError) as e:
                    print(f"Error processing event: {e}")
                    continue
        
        # Sort events by start time for each host
        for email in host_analytics:
            host_analytics[email]['events'].sort(key=lambda x: x['start_time'])
        
        return {
            'total_events': total_events,
            'hosts': host_analytics,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }