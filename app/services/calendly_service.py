# Enhanced CalendlyService with user-specific event fetching
# app/services/calendly_service.py

import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from app.config.settings import ConfigurationManager

class CalendlyService:
    """Enhanced service for Calendly API integration with team analytics"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.access_token = self.config_manager.get_app_config('CALENDLY_ACCESS_TOKEN')
        self.base_url = "https://api.calendly.com"
        self.user_uri = None  
        self.organization_uri: Optional[str] = None

    @staticmethod
    def _iso_z(dt: Optional[datetime]) -> Optional[str]:
        """Return UTC ISO-8601 ending with Z (Calendly requirement)."""
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    def _make_api_request(self, endpoint: str, method: str = 'GET', 
                         params: Optional[Dict] = None, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Calendly API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Calendly API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            return None

    def _ensure_user_and_org(self) -> bool:
        """Ensure we have user_uri and organization_uri cached."""
        if self.user_uri and self.organization_uri:
            return True

        user_data = self._make_api_request('/users/me')
        if not user_data or 'resource' not in user_data:
            print("Failed to get current user from Calendly")
            return False

        user = user_data['resource']
        self.user_uri = user.get('uri')
        
        # Get organization URI
        if 'current_organization' in user:
            self.organization_uri = user['current_organization']
        else:
            print("No organization found for user")
            return False

        return True

    def get_organization_users(self) -> Optional[Dict]:
        """Get all users in the organization"""
        if not self._ensure_user_and_org():
            return None

        params = {
            'organization': self.organization_uri,
            'count': 100  # Get up to 100 users
        }

        return self._make_api_request('/organization_memberships', params=params)

    def get_events_for_user_email(self, email: str, start_date: datetime, 
                                 end_date: datetime) -> List[Dict]:
        """Get events for a specific user by email address"""
        try:
            # First get organization users to find the user URI
            org_users = self.get_organization_users()
            if not org_users or 'collection' not in org_users:
                print(f"Could not get organization users for email lookup: {email}")
                return []

            # Find user URI by email
            user_uri = None
            for membership in org_users['collection']:
                user = membership.get('user', {})
                if user.get('email', '').lower() == email.lower():
                    user_uri = user.get('uri')
                    break

            if not user_uri:
                print(f"User not found in Calendly organization: {email}")
                return []

            # Get events for this specific user
            events_data = self.get_scheduled_events(start_date, end_date, user_uri=user_uri)
            
            if events_data and 'collection' in events_data:
                return events_data['collection']
            
            return []

        except Exception as e:
            print(f"Error getting events for user {email}: {e}")
            return []

    def get_scheduled_events(self, start_date: datetime = None, end_date: datetime = None, 
                           user_uri: str = None, organization_uri: str = None) -> Optional[Dict]:
        """Get scheduled events with flexible filtering"""
        if not self._ensure_user_and_org():
            return None

        # Use provided URIs or fall back to instance values
        target_user_uri = user_uri or self.user_uri
        target_org_uri = organization_uri or self.organization_uri

        # Default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        params = {
            'organization': target_org_uri,
            'min_start_time': self._iso_z(start_date),
            'max_start_time': self._iso_z(end_date),
            'count': 100,
            'sort': 'start_time:asc'
        }

        # Add user filter if specific user requested
        if user_uri:
            params['user'] = user_uri

        return self._make_api_request('/scheduled_events', params=params)

    def get_team_analytics_summary(self, team_members: List, start_date: datetime, 
                                  end_date: datetime) -> Dict:
        """Get comprehensive analytics for a team"""
        analytics = {
            'team_totals': {
                'total_events': 0,
                'completed_events': 0,
                'active_events': 0,
                'cancelled_events': 0
            },
            'member_breakdown': {}
        }

        try:
            # Get organization users once
            org_users = self.get_organization_users()
            if not org_users or 'collection' not in org_users:
                print("Could not fetch organization users")
                return analytics

            # Create email to URI mapping
            email_to_uri = {}
            for membership in org_users['collection']:
                user = membership.get('user', {})
                email = user.get('email', '').lower()
                if email:
                    email_to_uri[email] = user.get('uri')

            # Process each team member
            for member in team_members:
                member_email = member.email or f"{member.full_name.lower().replace(' ', '.')}@company.com"
                member_email = member_email.lower()

                if member_email in email_to_uri:
                    user_uri = email_to_uri[member_email]
                    events = self.get_scheduled_events(start_date, end_date, user_uri=user_uri)

                    if events and 'collection' in events:
                        member_stats = self._analyze_member_events(events['collection'])
                        analytics['member_breakdown'][member_email] = member_stats
                        
                        # Add to team totals
                        analytics['team_totals']['total_events'] += member_stats['total_events']
                        analytics['team_totals']['completed_events'] += member_stats['completed_events']
                        analytics['team_totals']['active_events'] += member_stats['active_events']
                        analytics['team_totals']['cancelled_events'] += member_stats['cancelled_events']
                    else:
                        analytics['member_breakdown'][member_email] = self._empty_member_stats()
                else:
                    print(f"Member email not found in Calendly: {member_email}")
                    analytics['member_breakdown'][member_email] = self._empty_member_stats()

        except Exception as e:
            print(f"Error getting team analytics: {e}")

        return analytics

    def _analyze_member_events(self, events: List[Dict]) -> Dict:
        """Analyze events for a single member"""
        stats = {
            'total_events': len(events),
            'completed_events': 0,
            'active_events': 0,
            'cancelled_events': 0,
            'booked': 0,
            'completed': 0
        }

        for event in events:
            status = event.get('status', '').lower()
            
            if status == 'active':
                stats['active_events'] += 1
                stats['booked'] += 1
            elif status == 'completed':
                stats['completed_events'] += 1 
                stats['completed'] += 1
            elif status == 'canceled':
                stats['cancelled_events'] += 1

        return stats

    def _empty_member_stats(self) -> Dict:
        """Return empty stats for members not found in Calendly"""
        return {
            'total_events': 0,
            'completed_events': 0,
            'active_events': 0,
            'cancelled_events': 0,
            'booked': 0,
            'completed': 0
        }

    def test_api_connection(self) -> Dict:
        """Test Calendly API connection"""
        try:
            if not self.access_token:
                return {'success': False, 'error': 'No access token configured'}

            user_data = self._make_api_request('/users/me')
            
            if user_data and 'resource' in user_data:
                user = user_data['resource']
                return {
                    'success': True,
                    'user_name': user.get('name'),
                    'user_email': user.get('email'),
                    'organization': user.get('current_organization')
                }
            else:
                return {'success': False, 'error': 'Failed to get user data'}

        except Exception as e:
            return {'success': False, 'error': str(e)}
        
