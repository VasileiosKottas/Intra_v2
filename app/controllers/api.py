"""
API controller for REST endpoints
"""

from flask import request, jsonify, session
from app.controllers.base import BaseController
from app.models import db
from app.models.advisor import Advisor
from app.models.team import Team
from app.models.sync_log import SyncLog
from app.services.sync import DataSyncService
from app.services.analytics import AnalyticsService
from app.services.date import DateService
from app.config.session import SessionManager
from app.config import config_manager

class APIController(BaseController):
    """Handles API routes"""
    
    def register_routes(self):
        """Register API routes"""
        # Company switching
        self.app.add_url_rule('/api/set-company', 'api.set_company', 
                             self.login_required(self.set_company), methods=['POST'])
        
        # Dashboard data
        self.app.add_url_rule('/api/dashboard-data', 'api.dashboard_data', 
                             self.login_required(self.get_dashboard_data))
        self.app.add_url_rule('/api/advisor-dashboard-data/<int:advisor_id>', 'api.advisor_dashboard_data',
                             self.master_required(self.get_advisor_dashboard_data))
        
        # User cases
        self.app.add_url_rule('/api/user-cases', 'api.user_cases', 
                             self.login_required(self.get_user_cases))
        self.app.add_url_rule('/api/advisor-cases/<int:advisor_id>', 'api.advisor_cases',
                             self.master_required(self.get_advisor_cases))
        
        # Team data
        self.app.add_url_rule('/api/team-data', 'api.team_data', 
                             self.login_required(self.get_team_data))
        self.app.add_url_rule('/api/advisor-team-data/<int:advisor_id>', 'api.advisor_team_data',
                             self.master_required(self.get_advisor_team_data))
        
        # Performance timeline
        self.app.add_url_rule('/api/performance-timeline', 'api.performance_timeline', 
                             self.login_required(self.get_performance_timeline))
        self.app.add_url_rule('/api/advisor-performance-timeline/<int:advisor_id>', 'api.advisor_performance_timeline',
                             self.master_required(self.get_advisor_performance_timeline))
        
        # Goal data
        self.app.add_url_rule('/api/user-goal-data', 'api.user_goal_data', 
                             self.login_required(self.get_user_goal_data))
        self.app.add_url_rule('/api/advisor-goal-data/<int:advisor_id>', 'api.advisor_goal_data',
                             self.master_required(self.get_advisor_goal_data))
        
        # Master API routes
        self.app.add_url_rule('/api/create-team', 'api.create_team', 
                             self.master_required(self.create_team), methods=['POST'])
        self.app.add_url_rule('/api/edit-team/<int:team_id>', 'api.edit_team',
                             self.master_required(self.edit_team), methods=['PUT'])
        self.app.add_url_rule('/api/delete-team/<int:team_id>', 'api.delete_team',
                             self.master_required(self.delete_team), methods=['DELETE'])
        self.app.add_url_rule('/api/assign-to-team', 'api.assign_to_team',
                             self.master_required(self.assign_to_team), methods=['POST'])
        self.app.add_url_rule('/api/unassign-from-team', 'api.unassign_from_team',
                             self.master_required(self.unassign_from_team), methods=['POST'])
        self.app.add_url_rule('/api/update-advisor-goal', 'api.update_advisor_goal',
                             self.master_required(self.update_advisor_goal), methods=['PUT'])
        self.app.add_url_rule('/api/sync-now', 'api.sync_now',
                             self.master_required(self.sync_now), methods=['POST'])
        self.app.add_url_rule('/api/sync-status', 'api.sync_status',
                             self.master_required(self.sync_status))
    
    def set_company(self):
        """Switch between company modes"""
        data = request.get_json()
        company = data.get('company', 'windsor')
        
        if not config_manager.is_valid_company(company):
            return jsonify({'error': 'Invalid company'}), 400
        
        SessionManager.set_current_company(session, company)
        return jsonify({'success': True, 'company': company})
    
    def get_dashboard_data(self):
        """Get main dashboard data for current user"""
        user = self.get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        # Calculate metrics using the advisor's method
        metrics = user.calculate_metrics_for_period(
            current_company, start_date, end_date,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        # Add referrals received calculation
        referrals_received = 0
        if user.full_name.lower() in ['steven horn', 'daniel jones']:
            all_submissions = user.get_submissions_for_period(current_company, start_date, end_date)
            referrals_received = len([r for r in all_submissions 
                                    if r.business_type and ('steve' in r.business_type.lower() or 'daniel' in r.business_type.lower())])
        
        metrics['referrals_received'] = referrals_received
        metrics['company'] = current_company
        
        return jsonify(metrics)
    
    def get_advisor_dashboard_data(self, advisor_id):
        """Get dashboard data for a specific advisor (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        # Calculate metrics using the advisor's method
        metrics = advisor.calculate_metrics_for_period(
            current_company, start_date, end_date,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        # Add referrals received calculation
        referrals_received = 0
        if advisor.full_name.lower() in ['steven horn', 'daniel jones']:
            all_submissions = advisor.get_submissions_for_period(current_company, start_date, end_date)
            referrals_received = len([r for r in all_submissions 
                                    if r.business_type and ('steve' in r.business_type.lower() or 'daniel' in r.business_type.lower())])
        
        metrics['referrals_received'] = referrals_received
        metrics['company'] = current_company
        metrics['advisor_name'] = advisor.full_name
        
        return jsonify(metrics)
    
    def get_user_cases(self):
        """Get cases for current user"""
        user = self.get_current_user()
        if not user:
            return jsonify([])

        current_company = SessionManager.get_current_company(session)
        case_type_filter = request.args.get('case_type', 'all')
        data_type = request.args.get('data_type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        return self._get_cases_data(user, current_company, case_type_filter, data_type, start_date, end_date)
    
    def get_advisor_cases(self, advisor_id):
        """Get cases for a specific advisor (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify([])

        current_company = SessionManager.get_current_company(session)
        case_type_filter = request.args.get('case_type', 'all')
        data_type = request.args.get('data_type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        return self._get_cases_data(advisor, current_company, case_type_filter, data_type, start_date, end_date)
    
    def _get_cases_data(self, advisor, current_company, case_type_filter, data_type, start_date, end_date):
        """Helper method to get cases data"""
        if data_type == 'submitted':
            all_submissions = advisor.get_submissions_for_period(current_company, start_date, end_date)
            valid_business_types = config_manager.get_valid_business_types(current_company)
            
            if case_type_filter == 'all':
                cases = [s for s in all_submissions if s.business_type in valid_business_types]
            else:
                cases = [s for s in all_submissions if s.business_type == case_type_filter]

            return jsonify([
                {
                    'customer_name': s.customer_name,
                    'case_type': s.business_type,
                    'fee_submitted': float(s.total_value),
                    'payment_status': 'Pending',
                    'date': s.submission_date.strftime('%d %b'),
                    'data_type': 'Submitted'
                } for s in sorted(cases, key=lambda x: x.submission_date, reverse=True)
            ])
        else:
            paid_cases = advisor.get_paid_cases_for_period(
                current_company, start_date, end_date,
                config_manager.get_valid_paid_case_types(current_company)
            )
            
            if case_type_filter != 'all':
                paid_cases = [p for p in paid_cases if p.case_type == case_type_filter]

            return jsonify([
                {
                    'customer_name': p.customer_name or 'Unknown Customer',
                    'case_type': p.case_type,
                    'fee_submitted': float(p.value or 0),
                    'payment_status': 'Paid',
                    'date': p.date_paid.strftime('%d %b'),
                    'data_type': 'Paid'
                } for p in sorted(paid_cases, key=lambda x: x.date_paid, reverse=True)
            ])
    
    def get_team_data(self):
        """Get team data for current user"""
        user = self.get_current_user()
        current_company = SessionManager.get_current_company(session)
        user_team = user.get_team_for_company(current_company)
        
        if not user_team:
            return jsonify({'no_team': True})

        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        # Get visible team members (excludes hidden team members for regular users)
        visible_members = self.get_visible_team_members(user, current_company)
        
        team_members = []
        for member in visible_members:
            metrics = member.calculate_metrics_for_period(
                current_company, start_date, end_date,
                config_manager.get_valid_business_types(current_company),
                config_manager.get_valid_paid_case_types(current_company)
            )
            
            yearly_goal = member.get_yearly_goal_for_company(current_company)
            goal_progress = (metrics['total_submitted'] / yearly_goal * 100) if yearly_goal > 0 else 0.0

            team_members.append({
                'name': member.full_name,
                'total_submitted': metrics['total_submitted'],
                'total_paid': metrics['total_paid'],
                'avg_case_size': (metrics['total_paid'] / metrics['paid_cases_count']) if metrics['paid_cases_count'] > 0 else 0.0,
                'goal_progress': goal_progress
            })

        team_members.sort(key=lambda m: m['total_submitted'], reverse=True)

        # Team monthly goal (always current month)
        month_start, today = DateService.get_current_month_dates()
        
        monthly_metrics = user_team.get_team_metrics_for_period(
            month_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        # For hidden teams, don't show team goals to regular members
        if user_team.is_hidden and not user.is_master:
            team_goal = 0.0
            team_progress = 0.0
        else:
            team_goal = float(user_team.monthly_goal or 0.0)
            team_progress = (monthly_metrics['total_submitted'] / team_goal * 100) if team_goal > 0 else 0.0
        
        days_left = DateService.days_left_in_month()

        return jsonify({
            'team_name': user_team.name if not user_team.is_hidden or user.is_master else 'Personal Goals',
            'team_members': team_members,
            'team_progress': team_progress,
            'team_monthly_total': monthly_metrics['total_submitted'],
            'team_monthly_goal': team_goal,
            'days_left': days_left,
            'total_paid': sum(m['total_paid'] for m in team_members),
            'company': current_company,
            'is_hidden_team': user_team.is_hidden if user_team else False
        })
    
    def get_advisor_team_data(self, advisor_id):
        """Get team data for a specific advisor (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        current_company = SessionManager.get_current_company(session)
        advisor_team = advisor.get_team_for_company(current_company) if advisor else None
        
        if not advisor or not advisor_team:
            return jsonify({'no_team': True})
        
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)

        team_members = []
        for member in advisor_team.members:
            metrics = member.calculate_metrics_for_period(
                current_company, start_date, end_date,
                config_manager.get_valid_business_types(current_company),
                config_manager.get_valid_paid_case_types(current_company)
            )
            
            yearly_goal = member.get_yearly_goal_for_company(current_company)
            goal_progress = (metrics['total_submitted'] / yearly_goal * 100) if yearly_goal > 0 else 0.0

            team_members.append({
                'name': member.full_name,
                'total_submitted': metrics['total_submitted'],
                'total_paid': metrics['total_paid'],
                'avg_case_size': (metrics['total_paid'] / metrics['paid_cases_count']) if metrics['paid_cases_count'] > 0 else 0.0,
                'goal_progress': goal_progress
            })

        team_members.sort(key=lambda m: m['total_submitted'], reverse=True)

        # Team monthly goal (always current month)
        month_start, today = DateService.get_current_month_dates()
        
        monthly_metrics = advisor_team.get_team_metrics_for_period(
            month_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        team_goal = float(advisor_team.monthly_goal or 0.0)
        team_progress = (monthly_metrics['total_submitted'] / team_goal * 100) if team_goal > 0 else 0.0
        days_left = DateService.days_left_in_month()

        return jsonify({
            'team_name': advisor_team.name,
            'team_members': team_members,
            'team_progress': team_progress,
            'team_monthly_total': monthly_metrics['total_submitted'],
            'team_monthly_goal': team_goal,
            'days_left': days_left,
            'total_paid': sum(m['total_paid'] for m in team_members),
            'company': current_company,
            'is_hidden_team': advisor_team.is_hidden
        })
    
    def get_performance_timeline(self):
        """Get performance timeline for current user"""
        user = self.get_current_user()
        if not user:
            return jsonify([])

        current_company = SessionManager.get_current_company(session)
        metric_type = request.args.get('type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        analytics_service = AnalyticsService(current_company)
        timeline_data = analytics_service.get_advisor_performance_timeline(
            user, period, metric_type, start_str, end_str
        )
        
        return jsonify(timeline_data)
    
    def get_advisor_performance_timeline(self, advisor_id):
        """Get performance timeline for a specific advisor (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify([])

        current_company = SessionManager.get_current_company(session)
        metric_type = request.args.get('type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        analytics_service = AnalyticsService(current_company)
        timeline_data = analytics_service.get_advisor_performance_timeline(
            advisor, period, metric_type, start_str, end_str
        )
        
        return jsonify(timeline_data)
    
    def get_user_goal_data(self):
        """Get user's yearly goal progress"""
        user = self.get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        year_start, today = DateService.get_current_year_dates()
        
        # Get yearly metrics
        yearly_metrics = user.calculate_metrics_for_period(
            current_company, year_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        user_yearly_goal = user.get_yearly_goal_for_company(current_company) or 50000.0
        user_yearly_progress = (yearly_metrics['total_submitted'] / user_yearly_goal * 100) if user_yearly_goal > 0 else 0.0
        user_yearly_remaining = max(0, user_yearly_goal - yearly_metrics['total_submitted'])
        days_left_year = DateService.days_left_in_year()
        
        return jsonify({
            'user_yearly_total': yearly_metrics['total_submitted'],
            'user_yearly_goal': user_yearly_goal,
            'user_yearly_progress': user_yearly_progress,
            'user_yearly_remaining': user_yearly_remaining,
            'days_left_year': days_left_year,
            'submissions_count': yearly_metrics['submissions_count'],
            'company': current_company
        })
    
    def get_advisor_goal_data(self, advisor_id):
        """Get advisor's yearly goal progress (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        year_start, today = DateService.get_current_year_dates()
        
        # Get yearly metrics
        yearly_metrics = advisor.calculate_metrics_for_period(
            current_company, year_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        advisor_yearly_goal = advisor.get_yearly_goal_for_company(current_company) or 50000.0
        advisor_yearly_progress = (yearly_metrics['total_submitted'] / advisor_yearly_goal * 100) if advisor_yearly_goal > 0 else 0.0
        advisor_yearly_remaining = max(0, advisor_yearly_goal - yearly_metrics['total_submitted'])
        days_left_year = DateService.days_left_in_year()
        
        return jsonify({
            'user_yearly_total': yearly_metrics['total_submitted'],
            'user_yearly_goal': advisor_yearly_goal,
            'user_yearly_progress': advisor_yearly_progress,
            'user_yearly_remaining': advisor_yearly_remaining,
            'days_left_year': days_left_year,
            'submissions_count': yearly_metrics['submissions_count'],
            'company': current_company,
            'advisor_name': advisor.full_name
        })
    
    # Master API methods
    def create_team(self):
        """Create a new team"""
        data = request.get_json()
        current_company = SessionManager.get_current_company(session)
        
        team = Team(
            name=data['name'],
            monthly_goal=float(data.get('monthly_goal', 0)),
            created_by=session['user_id'],
            company=current_company,
            is_hidden=data.get('is_hidden', False)
        )
        team.save()
        return jsonify({'success': True, 'team_id': team.id})
    
    def edit_team(self, team_id):
        """Edit team details"""
        data = request.get_json()
        team = db.session.get(Team, team_id)
        
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        if team.company != current_company:
            return jsonify({'error': 'Team not in current company'}), 403
        
        # Update team details
        team.name = data.get('name', team.name)
        team.monthly_goal = float(data.get('monthly_goal', team.monthly_goal))
        team.is_hidden = data.get('is_hidden', team.is_hidden)
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': f'Team {team.name} updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update goal'}), 500
    
    def sync_now(self):
        """Manual sync trigger for master"""
        current_company = SessionManager.get_current_company(session)
        sync_service = DataSyncService(current_company)
        submissions_added, paid_cases_added, success, error = sync_service.perform_sync()
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Sync completed for {current_company}',
                'submissions_added': submissions_added,
                'paid_cases_added': paid_cases_added
            })
        else:
            return jsonify({'error': f'Sync failed: {error}'}), 500
    
    def sync_status(self):
        """Get sync status and logs"""
        current_company = SessionManager.get_current_company(session)
        recent_syncs = SyncLog.query.filter_by(company=current_company).order_by(SyncLog.sync_time.desc()).limit(10).all()
        
        sync_data = []
        for sync in recent_syncs:
            sync_data.append({
                'time': sync.sync_time.strftime('%Y-%m-%d %H:%M:%S'),
                'submissions': sync.submissions_synced,
                'paid_cases': sync.paid_cases_synced,
                'status': sync.status,
                'error': sync.error_message,
                'company': sync.company
            })
        
        return jsonify(sync_data)
    
    def delete_team(self, team_id):
        """Delete a team and unassign all members"""
        team = db.session.get(Team, team_id)
        
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        if team.company != current_company:
            return jsonify({'error': 'Team not in current company'}), 403
        
        team_name = team.name
        
        try:
            team.delete()
            return jsonify({'success': True, 'message': f'Team {team_name} deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to delete team'}), 500
    
    def assign_to_team(self):
        """Assign an advisor to a team"""
        data = request.get_json()
        advisor_id = data.get('advisor_id')
        team_id = data.get('team_id')
        yearly_goal = data.get('yearly_goal', 0)
        
        if not advisor_id or not team_id:
            return jsonify({'error': 'Advisor ID and Team ID required'}), 400
        
        advisor = db.session.get(Advisor, advisor_id)
        team = db.session.get(Team, team_id)
        
        if not advisor or not team:
            return jsonify({'error': 'Advisor or Team not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        if team.company != current_company:
            return jsonify({'error': 'Team not in current company'}), 403
        
        success, message = team.add_member(advisor, float(yearly_goal))
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    
    def unassign_from_team(self):
        """Unassign an advisor from their team in current company"""
        data = request.get_json()
        advisor_id = data.get('advisor_id')
        
        if not advisor_id:
            return jsonify({'error': 'Advisor ID required'}), 400
        
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        current_team = advisor.get_team_for_company(current_company)
        
        if not current_team:
            return jsonify({'error': 'Advisor not assigned to any team in this company'}), 400
        
        success, message = current_team.remove_member(advisor)
        
        if success:
            return jsonify({'success': True, 'message': f'{advisor.full_name} unassigned from {current_team.name}'})
        else:
            return jsonify({'error': message}), 500
    

    def update_advisor_goal(self):
            """Update an advisor's yearly goal for the current company"""
            data = request.get_json()
            advisor_id = data.get('advisor_id')
            yearly_goal = data.get('yearly_goal')
            company = data.get('company', SessionManager.get_current_company(session))
            
            if not advisor_id or yearly_goal is None:
                return jsonify({'error': 'Advisor ID and yearly goal are required'}), 400
            
            advisor = db.session.get(Advisor, advisor_id)
            if not advisor:
                return jsonify({'error': 'Advisor not found'}), 404
            
            try:
                # Use the new method to set yearly goal (handles both team and individual goals)
                advisor.set_yearly_goal_for_company(company, float(yearly_goal))
                
                return jsonify({
                    'success': True, 
                    'message': f'Updated {advisor.full_name}\'s yearly goal to £{yearly_goal:,.0f} for {company.upper()}'
                })
            except ValueError:
                return jsonify({'error': 'Invalid yearly goal value'}), 400
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': f'Failed to update goal: {str(e)}'}), 500