from flask import request, jsonify, session
from app.controllers.base import BaseController
from app.services.calendly_service import CalendlyService
from datetime import datetime, timedelta

class CalendlyController(BaseController):
    """Handles Calendly integration with personal access token"""
    
    def register_routes(self):
        """Register Calendly API routes"""
        
        print("🔗 Registering Calendly routes...")
        
        try:
            # Debug route (no login required)
            self.app.add_url_rule('/api/calendly/debug', 'api.calendly_debug',
                                 self.debug_config, methods=['GET'])
            print("✓ Debug route registered")
            
            # Simple test route (no login required)
            self.app.add_url_rule('/api/calendly/simple-test', 'api.calendly_simple_test',
                                 self.simple_test, methods=['GET'])
            print("✓ Simple test route registered")
            
            # Team events test (no login required for now)
            self.app.add_url_rule('/api/calendly/team-events-test', 'api.calendly_team_events_test',
                                 self.get_team_events_test, methods=['GET'])
            print("✓ Team events test route registered")
            
            # Full team events report (requires login)
            self.app.add_url_rule('/api/calendly/team-events', 'api.calendly_team_events',
                                 self.login_required(self.get_team_events_report), methods=['GET'])
            print("✓ Team events report route registered")
            
            # Calendly users analytics (no login for testing)
            self.app.add_url_rule('/api/calendly/users-analytics', 'api.calendly_users_analytics',
                                 self.get_calendly_users_analytics, methods=['GET'])
            print("✓ Calendly users analytics route registered")
            
            # Complete events analytics with full details
            self.app.add_url_rule('/api/calendly/events-complete', 'api.calendly_events_complete',
                                 self.get_complete_events_analytics, methods=['GET'])
            print("✓ Complete events analytics route registered")
            
            # Add this to your register_routes method in CalendlyController
            self.app.add_url_rule('/api/calendly/host-analytics', 'api.calendly_host_analytics',
                                self.get_host_events_analytics, methods=['GET'])
    
        except Exception as e:
            print(f"❌ Error registering routes: {e}")
            import traceback
            traceback.print_exc()
        
        print("✅ Calendly routes registration complete")

    def test_calendly_debug(self):
        """Debug Calendly integration"""
        try:
            from app.services.calendly_service import CalendlyService
            calendly_service = CalendlyService()
            
            # Test connection
            connection_test = calendly_service.test_connection()
            
            # Get user info
            user_info = calendly_service.get_user_info()
            
            return jsonify({
                'calendly_connection': connection_test,
                'user_info': user_info,
                'token_configured': bool(calendly_service.access_token)
            })
            
        except Exception as e:
            return jsonify({'error': f'Debug failed: {str(e)}'})

    def debug_config(self):
        """Debug configuration loading"""
        import os
        from app.config import config_manager
        
        # Also debug team information
        try:
            from app.models.team import Team
            from app.config.session import SessionManager
            
            current_company = SessionManager.get_current_company(session)
            all_teams = Team.query.filter_by(company=current_company).all()
            
            team_info = [
                {
                    'id': team.id,
                    'name': team.name,
                    'is_hidden': team.is_hidden,
                    'member_count': len(team.members)
                }
                for team in all_teams
            ]
        except Exception as e:
            team_info = f"Error getting teams: {str(e)}"
        
        return jsonify({
            'status': 'working',
            'config_manager': config_manager.get_app_config('CALENDLY_ACCESS_TOKEN'),
            'token_length': len(config_manager.get_app_config('CALENDLY_ACCESS_TOKEN') or '') or 'None',
            'available_routes': [str(rule) for rule in self.app.url_map.iter_rules() if 'calendly' in str(rule)],
            'current_company': SessionManager.get_current_company(session) if 'session' in globals() else 'No session',
            'teams_in_company': team_info
        })
    
    def simple_test(self):
        """Simple test endpoint"""
        return jsonify({
            'message': 'Simple test route is working!',
            'timestamp': datetime.now().isoformat()
        })
    
    def get_team_events_test(self):
        """Test endpoint for team events without login requirement"""
        try:
            calendly_service = CalendlyService()
            
            # Test basic Calendly connection
            if not calendly_service.test_connection():
                return jsonify({'error': 'Calendly connection failed'})
            
            # Get events for last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            events_data = calendly_service.get_scheduled_events(
                start_time=start_date,
                end_time=end_date,
                count=50
            )
            
            total_events = 0
            events_list = []
            
            if events_data and 'collection' in events_data:
                events = events_data['collection']
                total_events = len(events)
                
                for event in events:
                    events_list.append({
                        'name': event.get('name'),
                        'start_time': event.get('start_time'),
                        'status': event.get('status'),
                        'uuid': event.get('uuid')
                    })
            
            return jsonify({
                'success': True,
                'message': 'Team events test - no authentication required',
                'total_events': total_events,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'events_sample': events_list[:5],  # First 5 events
            })
            
        except Exception as e:
            return jsonify({'error': f'Test failed: {str(e)}'})
    
    def get_team_events_report(self):
        """Get Calendly events report for team members (requires login)"""
        try:
            user = self.get_current_user()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            from app.config.session import SessionManager
            from app.models.team import Team

            current_company = SessionManager.get_current_company(session)
            
            # Get the user's team or requested team
            requested_team_id = request.args.get('team_id')
            
            if requested_team_id:
                try:
                    team_id = int(requested_team_id)
                    user_team = Team.query.get(team_id)
                    
                    # Verify user has access to this team
                    if not user.is_master:
                        user_team_ids = [membership.team.id for membership in user.team_memberships 
                                       if membership.team.company == current_company]
                        if team_id not in user_team_ids:
                            return jsonify({'error': 'Access denied to requested team'}), 403
                    
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid team ID'}), 400
            else:
                # Masters need to select a team - provide options
                if user.is_master:
                    from app.models.team import Team
                    available_teams = Team.query.filter_by(company=current_company).all()
                    
                    if not available_teams:
                        return jsonify({
                            'error': 'No teams found in company',
                            'suggestion': 'Create teams through the master dashboard first'
                        })
                    
                    return jsonify({
                        'error': 'Master users must specify a team_id',
                        'available_teams': [
                            {
                                'id': team.id,
                                'name': team.name,
                                'member_count': len(team.members),
                                'is_hidden': team.is_hidden
                            }
                            for team in available_teams
                        ],
                        'usage': f'Add ?team_id=X to the URL to view a specific team',
                        'example': f'/api/calendly/team-events?team_id={available_teams[0].id if available_teams else 1}'
                    })
                else:
                    # Regular users get their assigned team
                    user_team = user.get_primary_team_for_company(current_company)
            
            if not user_team:
                return jsonify({
                    'error': 'No team found',
                    'team_name': 'No Team',
                    'members': [],
                    'suggestion': 'Masters can specify a team_id parameter, or create/assign teams through the master dashboard'
                })

            # Parse date parameters
            days = request.args.get('days', 30, type=int)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Get team members (following your existing visibility logic)
            if user.is_master:
                # Masters can see all team members
                team_members = user_team.members
            else:
                # Regular users follow visibility rules
                if user_team.is_hidden:
                    # If user is in a hidden team, they only see themselves
                    team_members = [user]
                else:
                    # Regular team members see all members of visible teams only
                    team_members = []
                    for member in user_team.members:
                        member_team = member.get_team_for_company(current_company)
                        # Only include members who are not in hidden teams
                        if not member_team or not member_team.is_hidden:
                            team_members.append(member)

            # Get Calendly service and user-specific analytics
            calendly_service = CalendlyService()
            
            # Get events broken down by Calendly users
            calendly_user_analytics = calendly_service.get_analytics_data_by_user(start_date, end_date)
            calendly_users = calendly_user_analytics.get('users', {})
            total_calendly_events = calendly_user_analytics.get('total_events', 0)
            
            # Create email-to-events mapping for easier lookup
            calendly_events_by_email = {}
            for user_uri, user_data in calendly_users.items():
                email = user_data.get('email', '').lower()
                if email:
                    calendly_events_by_email[email] = {
                        'name': user_data.get('name'),
                        'events_count': user_data.get('events_count', 0),
                        'events': user_data.get('events', [])
                    }
            
            # Build team member report with Calendly data integration
            team_member_reports = []
            for member in team_members:
                # Match team member email with Calendly user email
                member_email = member.email.lower()
                calendly_data = calendly_events_by_email.get(member_email, {})
                
                member_events_count = calendly_data.get('events_count', 0)
                member_events_list = calendly_data.get('events', [])
                calendly_name = calendly_data.get('name', 'Not found in Calendly')
                
                # Calculate submission metrics for comparison
                from app.services.date import DateService
                from app.config import config_manager
                
                submission_metrics = member.calculate_metrics_for_period(
                    current_company, start_date, end_date,
                    config_manager.get_valid_business_types(current_company),
                    config_manager.get_valid_paid_case_types(current_company)
                )
                
                team_member_reports.append({
                    'advisor_id': member.id,
                    'advisor_name': member.full_name,
                    'username': member.username,
                    'email': member.email,
                    'calendly_events_count': member_events_count,
                    'calendly_name': calendly_name,
                    'has_calendly_account': member_email in calendly_events_by_email,
                    'recent_events': member_events_list[-3:],  # Last 3 events
                    'submission_metrics': {
                        'total_submitted': submission_metrics.get('total_submitted', 0),
                        'total_paid': submission_metrics.get('total_paid', 0),
                        'submissions_count': submission_metrics.get('submissions_count', 0)
                    }
                })

            # Sort by Calendly events count (descending), then by submission metrics
            team_member_reports.sort(key=lambda x: (x['calendly_events_count'], x['submission_metrics']['total_submitted']), reverse=True)
            
            # Calculate events by date from all team members
            events_by_date = {}
            for user_data in calendly_users.values():
                for event in user_data.get('events', []):
                    try:
                        event_time = datetime.fromisoformat(event['start_time'])
                        date_key = event_time.date().isoformat()
                        events_by_date[date_key] = events_by_date.get(date_key, 0) + 1
                    except (ValueError, TypeError):
                        continue

            return jsonify({
                'success': True,
                'team_name': user_team.name,
                'team_id': user_team.id,
                'company': current_company,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'total_team_events': total_calendly_events,
                'events_by_date': dict(sorted(events_by_date.items())),
                'team_members': team_member_reports,
                'calendly_integration_summary': {
                    'total_calendly_users': len(calendly_users),
                    'team_members_with_calendly': sum(1 for member in team_member_reports if member['has_calendly_account']),
                    'team_members_without_calendly': sum(1 for member in team_member_reports if not member['has_calendly_account'])
                }
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_calendly_users_analytics(self):
        """Get Calendly analytics broken down by users (test endpoint)"""
        try:
            calendly_service = CalendlyService()
            
            # Parse date parameters
            days = request.args.get('days', 30, type=int)
            end_date_str = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            start_date_str = request.args.get('start_date')
            

            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Use provided start_date or default to start of year
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            else:
                start_date = datetime(end_date.year, 1, 1)  # Default to YTD
            # Get user-specific analytics
            analytics_data = calendly_service.get_analytics_data_by_user(start_date, end_date)
            
            return jsonify({
                'success': True,
                'message': 'Calendly users analytics',
                'date_range': analytics_data.get('date_range', {}),
                'total_events': analytics_data.get('total_events', 0),
                'users': analytics_data.get('users', {}),
                'user_count': len(analytics_data.get('users', {}))
            })
            
        except Exception as e:
            return jsonify({'error': f'Analytics failed: {str(e)}'})
    
    def get_complete_events_analytics(self):
        """Get complete Calendly events analytics with full event details and participation analysis"""
        try:
            calendly_service = CalendlyService()
            
            # Parse date parameters
            days = request.args.get('days', 14, type=int)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get user analytics (which now analyzes event memberships properly)
            analytics_data = calendly_service.get_analytics_data_by_user(start_date, end_date)
            
            if 'error' in analytics_data:
                return jsonify({'error': analytics_data['error']}), 500
            
            # Also get all events for detailed analysis
            all_events = calendly_service.get_scheduled_events(start_date, end_date, count=100)
            
            detailed_events = []
            events_by_date = {}
            events_by_status = {}
            events_by_type = {}
            participant_summary = {}
            
            if all_events and 'collection' in all_events:
                for event in all_events['collection']:
                    start_time_str = event.get('start_time', '')
                    if not start_time_str:
                        continue
                        
                    try:
                        event_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        event_time = event_time.replace(tzinfo=None)
                        
                        # Process participants
                        participants = []
                        for membership in event.get('event_memberships', []):
                            participant = {
                                'user_uri': membership.get('user'),
                                'name': membership.get('user_name'),
                                'email': membership.get('user_email'),
                                'buffered_start_time': membership.get('buffered_start_time'),
                                'buffered_end_time': membership.get('buffered_end_time')
                            }
                            participants.append(participant)
                            
                            # Count by participant
                            participant_name = participant['name']
                            if participant_name:
                                participant_summary[participant_name] = participant_summary.get(participant_name, 0) + 1
                        
                        # Count by date
                        date_key = event_time.date().isoformat()
                        events_by_date[date_key] = events_by_date.get(date_key, 0) + 1
                        
                        # Count by status
                        status = event.get('status', 'unknown')
                        events_by_status[status] = events_by_status.get(status, 0) + 1
                        
                        # Count by event type (extract name from URI)
                        event_type_uri = event.get('event_type', '')
                        event_type_name = event_type_uri.split('/')[-1] if event_type_uri else 'unknown'
                        events_by_type[event_type_name] = events_by_type.get(event_type_name, 0) + 1
                        
                        # Build complete event data
                        detailed_event = {
                            'uri': event.get('uri'),
                            'name': event.get('name'),
                            'start_time': event_time.isoformat(),
                            'end_time': event.get('end_time'),
                            'status': status,
                            'event_type': event.get('event_type'),
                            'location': event.get('location', {}),
                            'participants': participants,
                            'participant_count': len(participants),
                            'invitees_counter': event.get('invitees_counter', {}),
                            'created_at': event.get('created_at'),
                            'updated_at': event.get('updated_at'),
                            'cancellation': event.get('cancellation'),
                            'meeting_notes_plain': event.get('meeting_notes_plain'),
                            'meeting_notes_html': event.get('meeting_notes_html')
                        }
                        
                        detailed_events.append(detailed_event)
                        
                    except (ValueError, TypeError) as e:
                        print(f"Error processing event: {e}")
                        continue
            
            # Sort events by start time
            detailed_events.sort(key=lambda x: x['start_time'])
            
            # Sort participant summary by event count
            participant_summary = dict(sorted(participant_summary.items(), key=lambda x: x[1], reverse=True))
            
            return jsonify({
                'success': True,
                'summary': {
                    'total_events': len(detailed_events),
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'days': days
                    },
                    'events_by_date': dict(sorted(events_by_date.items())),
                    'events_by_status': events_by_status,
                    'events_by_type': events_by_type,
                    'participant_summary': participant_summary
                },
                'detailed_events': detailed_events,
                'user_analytics': analytics_data.get('users', {}),
                'calendly_integration_info': {
                    'total_calendly_users': len(analytics_data.get('users', {})),
                    'events_analyzed': len(detailed_events),
                    'unique_participants': len(participant_summary)
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Complete analytics failed: {str(e)}'}), 500
    
    def debug_teams(self):
        """Debug team assignments and user info"""
        try:
            user = self.get_current_user()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            from app.config.session import SessionManager
            from app.models.team import Team

            current_company = SessionManager.get_current_company(session)
            
            # Get all teams for the company
            all_teams = Team.query.filter_by(company=current_company).all()
            
            # Get user's team memberships
            user_teams = user.get_teams_for_company(current_company)
            primary_team = user.get_primary_team_for_company(current_company)
            
            return jsonify({
                'current_user': {
                    'id': user.id,
                    'name': user.full_name,
                    'username': user.username,
                    'email': user.email,
                    'is_master': user.is_master
                },
                'current_company': current_company,
                'all_teams_in_company': [
                    {
                        'id': team.id,
                        'name': team.name,
                        'is_hidden': team.is_hidden,
                        'member_count': len(team.members)
                    }
                    for team in all_teams
                ],
                'user_teams': [
                    {
                        'id': team.id,
                        'name': team.name,
                        'is_hidden': team.is_hidden
                    }
                    for team in user_teams
                ],
                'primary_team': {
                    'id': primary_team.id,
                    'name': primary_team.name,
                    'is_hidden': primary_team.is_hidden
                } if primary_team else None
            })
            
        except Exception as e:
            return jsonify({'error': f'Debug failed: {str(e)}'})
        
    def get_host_events_analytics(self):
        """Get Calendly events analytics for specific hosts based on event ownership"""
        try:
            calendly_service = CalendlyService()
            
            # Parse date parameters
            days = request.args.get('days', 60, type=int)
            end_date_str = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            start_date_str = request.args.get('start_date')
            

            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Use provided start_date or default to start of year
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            else:
                start_date = datetime(end_date.year, 1, 1)  # Default to YTD
            
            # Define the hosts you want to track
            host_emails = [
                'mike.olivieri@windsorhillmortgages.co.uk',
                'daniel.jones@windsorhillmortgages.co.uk',
                'drew.gibson@windsorhillmortgages.co.uk'
            ]
            
            # Get corrected host-specific analytics
            analytics_data = calendly_service.get_correct_host_analytics_data(host_emails, start_date, end_date)
            
            if 'error' in analytics_data:
                return jsonify({'error': analytics_data['error']}), 500
            
            # Format the response with completed events count
            host_summary = {}
            for email, data in analytics_data['hosts'].items():
                if not data['user_found']:
                    continue
                    
                # Count only active events (completed meetings)
                # In Calendly, "active" means the event occurred, "canceled" means it was canceled
                completed_events = data['events_by_status'].get('active', 0)
                canceled_events = data['events_by_status'].get('canceled', 0)
                
                # Extract name from email
                name = email.split('@')[0].replace('.', ' ').title()
                
                host_summary[name] = {
                    'total_events': data['events_count'],
                    'completed_events': completed_events,
                    'canceled_events': canceled_events,
                    'events_by_type': data['events_by_type'],
                    'recent_events': data['events'][-5:],  # Last 5 events
                    'email': email,
                    'user_found': data['user_found'],
                    'user_uri': data['user_uri']
                }
            
            # Sort by completed events
            sorted_hosts = dict(sorted(host_summary.items(), 
                                    key=lambda x: x[1]['completed_events'], 
                                    reverse=True))
            # print(sorted_hosts)
            return jsonify({
                'success': True,
                'message': 'Host analytics based on event ownership (not participation)',
                'summary': {
                    'total_events': analytics_data['total_events'],
                    'date_range': analytics_data['date_range'],
                    'hosts_tracked': len([h for h in analytics_data['hosts'].values() if h['user_found']])
                },
                'host_analytics': sorted_hosts,
                'debug_info': {
                    'method_used': 'user-specific event queries',
                    'explanation': 'Each host\'s events fetched using their user URI, not organization-wide filtering'
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Host analytics failed: {str(e)}'}), 500