"""
API controller for REST endpoints - Updated with Referral Management
"""

from flask import request, jsonify, session
from app.controllers.base import BaseController
from app.models import db
from app.models.advisor import Advisor
from app.models.team import Team
from app.models.sync_log import SyncLog
from app.models.referral_recipient import ReferralRecipient
from app.models.submission import Submission

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
                # Get advisor's current teams
        self.app.add_url_rule('/api/advisor-teams/<int:advisor_id>', 'api.advisor_teams',
                             self.master_required(self.get_advisor_teams), methods=['GET'])
        
        # Get available teams for advisor (teams they're not in)
        self.app.add_url_rule('/api/available-teams/<int:advisor_id>', 'api.available_teams',
                             self.master_required(self.get_available_teams), methods=['GET'])

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
        
        # Referral management routes (NEW)
        self.app.add_url_rule('/api/referral-recipients', 'api.get_referral_recipients', 
                            self.master_required(self.get_referral_recipients), methods=['GET'])
        self.app.add_url_rule('/api/referral-recipients', 'api.set_referral_recipient',
                            self.master_required(self.set_referral_recipient), methods=['POST'])

        # You might also want to add a DELETE route for removing recipients
        self.app.add_url_rule('/api/referral-recipients/<int:advisor_id>', 'api.remove_referral_recipient',
                            self.master_required(self.remove_referral_recipient), methods=['DELETE'])


        # Change password
        self.app.add_url_rule('/api/update-user-credentials', 'api.update_user_credentials',
                            self.master_required(self.update_user_credentials), methods=['PUT'])
        self.app.add_url_rule('/api/reset-user-password', 'api.reset_user_password',
                            self.master_required(self.reset_user_password), methods=['POST'])
        self.app.add_url_rule('/api/get-user-details/<int:user_id>', 'api.get_user_details',
                            self.master_required(self.get_user_details))

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

        # Box plot performance data
        self.app.add_url_rule('/api/performance-boxplot', 'api.performance_boxplot', 
                            self.login_required(self.get_performance_boxplot))
        self.app.add_url_rule('/api/advisor-performance-boxplot/<int:advisor_id>', 'api.advisor_performance_boxplot',
                            self.master_required(self.get_advisor_performance_boxplot))


        self.app.add_url_rule('/api/debug-referrals', 'api.debug_referrals',
                            self.login_required(self.debug_referrals), methods=['GET'])
        self.app.add_url_rule('/api/debug-dashboard-calc', 'api.debug_dashboard_calc',
                            self.login_required(self.debug_dashboard_calculation), methods=['GET'])

        # Advisor sync route (allows regular advisors to sync data)
        self.app.add_url_rule('/api/advisor-sync', 'api.advisor_sync',
                            self.login_required(self.advisor_sync), methods=['POST'])
        
        self.app.add_url_rule('/api/debug-all-referrals', 'api.debug_all_referrals',
                             self.login_required(self.debug_all_referrals), methods=['GET'])

        # Referral mapping management routes
        self.app.add_url_rule('/api/referral-mappings', 'api.get_referral_mappings',
                            self.master_required(self.get_referral_mappings), methods=['GET'])
        self.app.add_url_rule('/api/referral-mappings', 'api.add_referral_mapping',
                            self.master_required(self.add_referral_mapping), methods=['POST'])
        self.app.add_url_rule('/api/referral-mappings/<int:mapping_id>', 'api.remove_referral_mapping',
                            self.master_required(self.remove_referral_mapping), methods=['DELETE'])
        self.app.add_url_rule('/api/unmapped-referrals', 'api.get_unmapped_referrals',
                            self.master_required(self.get_unmapped_referrals), methods=['GET'])
        # Get user's teams for team selector
        self.app.add_url_rule('/api/user-teams', 'api.user_teams',
                             self.login_required(self.get_user_teams), methods=['GET'])

    def get_user_teams(self):
        """Get user's teams - filter out hidden teams for non-master users"""
        user = self.get_current_user()
        current_company = SessionManager.get_current_company(session)
        
        teams_data = []
        for membership in user.team_memberships:
            team = membership.team
            if team.company == current_company:
                # Only include visible teams for non-master users
                if not team.is_hidden or user.is_master:
                    teams_data.append({
                        'id': team.id,
                        'name': team.name,
                        'is_hidden': team.is_hidden if user.is_master else False,  # Don't expose hidden status to regular users
                        'is_current_view': True,  # Will be updated based on selection
                        'monthly_goal': float(team.monthly_goal or 0.0)
                    })
        
        return jsonify(teams_data)
            
    def set_company(self):
        """Switch between company modes"""
        data = request.get_json()
        company = data.get('company', 'windsor')
        
        if not config_manager.is_valid_company(company):
            return jsonify({'error': 'Invalid company'}), 400
        
        SessionManager.set_current_company(session, company)
        return jsonify({'success': True, 'company': company})

    def _check_referral_match(self, referral_to_value, advisor_full_name, advisor_id, current_company):
        """Check if a referral_to value matches an advisor using database mappings"""
        if not referral_to_value or not advisor_full_name:
            return False
        
        referral_to_lower = referral_to_value.lower().strip()
        advisor_name_lower = advisor_full_name.lower().strip()
        
        # First check database mappings
        from app.models.referral_mapping import ReferralMapping
        mapped_advisor_id = ReferralMapping.get_advisor_for_referral(referral_to_value, current_company)
        if mapped_advisor_id == advisor_id:
            return True
        
        # Fallback to hardcoded mappings for backward compatibility
        hardcoded_mappings = self._get_referral_name_mappings()
        mapped_name = hardcoded_mappings.get(referral_to_lower)
        if mapped_name and mapped_name.lower() == advisor_name_lower:
            return True
        
        # Direct name match
        if advisor_name_lower in referral_to_lower or referral_to_lower in advisor_name_lower:
            return True
        
        # Check if advisor name contains first name from referral
        advisor_first_name = advisor_name_lower.split()[0] if advisor_name_lower else ""
        if advisor_first_name and advisor_first_name in referral_to_lower:
            return True
        
        return False

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
        
        # FIXED: Calculate referrals received with database mappings
        referrals_received = 0
        
        # Check if user is a referral recipient for current company
        if ReferralRecipient.is_referral_recipient(user.id, current_company):
            # Get ALL referrals for the company and period
            from app.models.submission import Submission
            all_referrals = Submission.query.filter(
                Submission.company == current_company,
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.business_type == 'Referral'
            ).all()
            
            # Count referrals that match this user using improved matching with database
            for referral in all_referrals:
                if self._check_referral_match(referral.referral_to, user.full_name, user.id, current_company):
                    referrals_received += 1
        
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
        
        # FIXED: Calculate referrals received with database mappings
        referrals_received = 0
        
        # Check if advisor is a referral recipient for current company
        if ReferralRecipient.is_referral_recipient(advisor.id, current_company):
            # Get ALL referrals for the company and period
            from app.models.submission import Submission
            all_referrals = Submission.query.filter(
                Submission.company == current_company,
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.business_type == 'Referral'
            ).all()
            
            # Count referrals that match this advisor using improved matching with database
            for referral in all_referrals:
                if self._check_referral_match(referral.referral_to, advisor.full_name, advisor.id, current_company):
                    referrals_received += 1
        
        metrics['referrals_received'] = referrals_received
        metrics['company'] = current_company
        metrics['advisor_name'] = advisor.full_name
        
        return jsonify(metrics)
    
    def get_referral_mappings(self):
        """Get all referral mappings for current company"""
        current_company = SessionManager.get_current_company(session)
        
        from app.models.referral_mapping import ReferralMapping
        mappings = ReferralMapping.get_mappings_for_company(current_company)
        
        return jsonify([{
            'id': mapping.id,
            'referral_name': mapping.referral_name,
            'advisor_id': mapping.advisor_id,
            'advisor_name': mapping.advisor.full_name,
            'company': mapping.company,
            'is_active': mapping.is_active
        } for mapping in mappings])

    def add_referral_mapping(self):
        """Add a new referral mapping"""
        data = request.get_json()
        referral_name = data.get('referral_name', '').strip()
        advisor_id = data.get('advisor_id')
        
        if not referral_name or not advisor_id:
            return jsonify({'error': 'Referral name and advisor ID are required'}), 400
        
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        
        try:
            from app.models.referral_mapping import ReferralMapping
            ReferralMapping.add_mapping(referral_name, advisor_id, current_company)
            
            return jsonify({
                'success': True,
                'message': f'Added mapping: "{referral_name}" → {advisor.full_name}'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to add mapping: {str(e)}'}), 500

    def remove_referral_mapping(self, mapping_id):
        """Remove a referral mapping"""
        try:
            from app.models.referral_mapping import ReferralMapping
            success = ReferralMapping.remove_mapping(mapping_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Mapping removed successfully'
                })
            else:
                return jsonify({'error': 'Mapping not found'}), 404
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to remove mapping: {str(e)}'}), 500

    def get_unmapped_referrals(self):
        """Get referral names that don't have mappings yet"""
        current_company = SessionManager.get_current_company(session)
        
        # Get all unique referral_to values from submissions
        from app.models.submission import Submission
        from app.models.referral_mapping import ReferralMapping
        
        all_referrals = db.session.query(Submission.referral_to).filter(
            Submission.company == current_company,
            Submission.business_type == 'Referral',
            Submission.referral_to.isnot(None),
            Submission.referral_to != ''
        ).distinct().all()
        
        # Get existing mappings
        existing_mappings = {m.referral_name for m in ReferralMapping.get_mappings_for_company(current_company)}
        
        # Find unmapped referrals
        unmapped = []
        for (referral_to,) in all_referrals:
            if referral_to and referral_to.lower().strip() not in existing_mappings:
                unmapped.append(referral_to)
        
        return jsonify(sorted(unmapped))

    # NEW REFERRAL MANAGEMENT METHODS
    def get_referral_recipients(self):
        """Get all referral recipients for current company"""
        current_company = SessionManager.get_current_company(session)
        
        recipients = ReferralRecipient.get_recipients_for_company(current_company)
        
        return jsonify([{
            'id': recipient.id,
            'advisor_id': recipient.advisor_id,
            'advisor_name': recipient.advisor.full_name,
            'company': recipient.company,
            'is_active': recipient.is_active
        } for recipient in recipients])

    def set_referral_recipient(self):
        """Set or update referral recipient status"""
        data = request.get_json()
        advisor_id = data.get('advisor_id')
        is_active = data.get('is_active', True)
        
        if not advisor_id:
            return jsonify({'error': 'Advisor ID required'}), 400
        
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        
        try:
            ReferralRecipient.set_referral_recipient(advisor_id, current_company, is_active)
            
            action = "enabled" if is_active else "disabled"
            return jsonify({
                'success': True,
                'message': f'Referral receiving {action} for {advisor.full_name} in {current_company.upper()}'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to update referral recipient: {str(e)}'}), 500

    def remove_referral_recipient(self, advisor_id):
        """Remove referral recipient status"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        
        try:
            ReferralRecipient.set_referral_recipient(advisor_id, current_company, False)
            
            return jsonify({
                'success': True,
                'message': f'Referral receiving disabled for {advisor.full_name} in {current_company.upper()}'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to remove referral recipient: {str(e)}'}), 500
    
    # Continue with existing methods...
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

    def get_advisor_teams(self, advisor_id):
        """Get all teams an advisor is currently in"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        teams = advisor.get_teams_for_company(current_company)
        
        team_data = []
        for team in teams:
            # Get the yearly goal for this specific team membership
            yearly_goal = 0.0
            for membership in advisor.team_memberships:
                if membership.team.id == team.id:
                    yearly_goal = membership.yearly_goal
                    break
            
            team_data.append({
                'id': team.id,
                'name': team.name,
                'monthly_goal': team.monthly_goal,
                'yearly_goal': yearly_goal,
                'is_hidden': team.is_hidden,
                'company': team.company
            })
        
        return jsonify(team_data)     


    def get_available_teams(self, advisor_id):
        """Get teams that an advisor is NOT currently in"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        
        # Get all teams for current company
        all_teams = Team.query.filter_by(company=current_company).all()
        
        # Get teams advisor is currently in
        advisor_team_ids = {team.id for team in advisor.get_teams_for_company(current_company)}
        
        # Filter out teams advisor is already in
        available_teams = [
            {
                'id': team.id,
                'name': team.name,
                'monthly_goal': team.monthly_goal,
                'is_hidden': team.is_hidden,
                'company': team.company
            }
            for team in all_teams
            if team.id not in advisor_team_ids
        ]
        
        return jsonify(available_teams)
 

    def get_visible_team_members(self, user: Advisor, current_company: str) -> list:
        """Get team members excluding those in hidden teams for regular users"""
        user_team = user.get_team_for_company(current_company)
        
        if user.is_master:
            # Masters can see all team members
            return user_team.members if user_team else []
        
        if not user_team:
            # No team assignment
            return []
        
        if user_team.is_hidden:
            # If user is in a hidden team, they only see themselves (team is invisible to them)
            return [user]
        
        # Regular team members see all members of visible teams only
        visible_members = []
        for member in user_team.members:
            member_team = member.get_team_for_company(current_company)
            # Only include members who are not in hidden teams
            if not member_team or not member_team.is_hidden:
                visible_members.append(member)
        
        return visible_members
    
    def get_team_data(self):
        """Get team data for current user - supports team switching via team_id parameter"""
        user = self.get_current_user()
        current_company = SessionManager.get_current_company(session)
        
        # Check if a specific team is being requested (for team switching)
        requested_team_id = request.args.get('team_id')
        
        if requested_team_id:
            # User is switching to view a specific team
            try:
                requested_team_id = int(requested_team_id)
                requested_team = Team.query.get(requested_team_id)
                
                # Verify user has access to this team
                user_team_ids = [membership.team.id for membership in user.team_memberships 
                            if membership.team.company == current_company]
                
                if requested_team_id not in user_team_ids:
                    return jsonify({'error': 'Access denied to requested team'}), 403
                
                user_team = requested_team
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid team ID'}), 400
        else:
            # Default behavior - get user's primary team
            user_team = user.get_team_for_company(current_company)
        
        if not user_team:
            return jsonify({'no_team': True})

        # For hidden teams, completely hide them from non-master users
        if user_team.is_hidden and not user.is_master:
            return jsonify({
                'no_team': True,
                'is_hidden_team': True,
                'is_master_user': False
            })

        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        # Get team members for the selected team (not just user's primary team)
        if user.is_master:
            # Masters can see all team members
            visible_members = user_team.members
        else:
            if user_team.is_hidden:
                # If viewing a hidden team, only show self
                visible_members = [user]
            else:
                # For visible teams, show all members who are not in hidden teams
                visible_members = [member for member in user_team.members 
                                if not member.get_team_for_company(current_company) or 
                                not member.get_team_for_company(current_company).is_hidden]
        
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

        # Team monthly goal (always current month) - for the SELECTED team
        month_start, today = DateService.get_current_month_dates()
        
        monthly_metrics = user_team.get_team_metrics_for_period(
            month_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        team_goal = float(user_team.monthly_goal or 0.0)
        team_progress = (monthly_metrics['total_submitted'] / team_goal * 100) if team_goal > 0 else 0.0
        
        days_left = DateService.days_left_in_month()

        # Count only visible teams for the user
        user_visible_teams = [team for membership in user.team_memberships 
                            for team in [membership.team] 
                            if team.company == current_company and (not team.is_hidden or user.is_master)]

        return jsonify({
            'team_name': user_team.name,
            'team_members': team_members,
            'team_progress': team_progress,
            'team_monthly_total': monthly_metrics['total_submitted'],
            'team_monthly_goal': team_goal,
            'days_left': days_left,
            'total_paid': sum(m['total_paid'] for m in team_members),
            'company': current_company,
            'user_teams_count': len(user_visible_teams),
            'is_hidden_team': False,  # Never expose hidden team status to frontend
            'is_master_user': user.is_master,
            'current_team_id': user_team.id  # Include current team ID for frontend reference
        })
    
    def get_advisor_team_data(self, advisor_id):
        """Get team data for a specific advisor - ENHANCED with team_id support (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        current_company = SessionManager.get_current_company(session)
        
        # Check if specific team was requested
        requested_team_id = request.args.get('team_id')
        
        if requested_team_id:
            # Get specific team data
            try:
                team_id = int(requested_team_id)
                requested_team = db.session.get(Team, team_id)
                
                if not requested_team or requested_team.company != current_company:
                    return jsonify({'error': 'Team not found'}), 404
                
                display_team = requested_team
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid team ID'}), 400
        else:
            # Get advisor's primary team
            display_team = advisor.get_primary_team_for_company(current_company) if advisor else None
        
        if not advisor or not display_team:
            return jsonify({'no_team': True})
        
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)

        # Masters can see all team members
        team_members = []
        for member in display_team.members:
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
        
        monthly_metrics = display_team.get_team_metrics_for_period(
            month_start, today,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        team_goal = float(display_team.monthly_goal or 0.0)
        team_progress = (monthly_metrics['total_submitted'] / team_goal * 100) if team_goal > 0 else 0.0
        days_left = DateService.days_left_in_month()

        return jsonify({
            'team_name': display_team.name,
            'team_members': team_members,
            'team_progress': team_progress,
            'team_monthly_total': monthly_metrics['total_submitted'],
            'team_monthly_goal': team_goal,
            'days_left': days_left,
            'total_paid': sum(m['total_paid'] for m in team_members),
            'company': current_company,
            'is_hidden_team': display_team.is_hidden,
            'user_teams_count': len(advisor.get_teams_for_company(current_company)),
            'advisor_name': advisor.full_name,
            'requested_team_id': requested_team_id,
            'can_switch_teams': len(advisor.get_teams_for_company(current_company)) > 1
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
            # First, manually remove all team memberships
            for membership in list(team.advisor_memberships):
                db.session.delete(membership)
            
            # Flush to ensure memberships are deleted before team deletion
            db.session.flush()
            
            # Now delete the team
            db.session.delete(team)
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'Team {team_name} deleted successfully'})
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting team: {str(e)}")  # For debugging
            return jsonify({'error': 'Failed to delete team'}), 500

    def assign_to_team(self):
        """Assign an advisor to a team - UPDATED to allow multiple teams"""
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
        
        # Updated to allow multiple teams (allow_multiple=True by default)
        success, message = team.add_member(advisor, float(yearly_goal), allow_multiple=True)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    def unassign_from_team(self):
        """Unassign an advisor from a SPECIFIC team in current company"""
        data = request.get_json()
        advisor_id = data.get('advisor_id')
        team_id = data.get('team_id')  # NEW: Specific team ID
        
        if not advisor_id:
            return jsonify({'error': 'Advisor ID required'}), 400
        
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'error': 'Advisor not found'}), 404
        
        current_company = SessionManager.get_current_company(session)
        
        if team_id:
            # Unassign from specific team
            team = db.session.get(Team, team_id)
            if not team or team.company != current_company:
                return jsonify({'error': 'Team not found or not in current company'}), 404
            
            success, message = team.remove_member(advisor)
            team_name = team.name
        else:
            # Unassign from primary team (backward compatibility)
            primary_team = advisor.get_primary_team_for_company(current_company)
            if not primary_team:
                return jsonify({'error': 'Advisor not assigned to any team in this company'}), 400
            
            success, message = primary_team.remove_member(advisor)
            team_name = primary_team.name
        
        if success:
            return jsonify({'success': True, 'message': f'{advisor.full_name} unassigned from {team_name}'})
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
    
    def update_user_credentials(self):
        """Update user's email, username, and optionally password"""
        data = request.get_json()
        user_id = data.get('user_id')
        new_email = data.get('email', '').strip()
        new_username = data.get('username', '').strip()
        new_password = data.get('password', '').strip()
        
        if not user_id or not new_email or not new_username:
            return jsonify({'error': 'User ID, email, and username are required'}), 400
        
        advisor = db.session.get(Advisor, user_id)
        if not advisor:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if username already exists (excluding current user)
        existing_username = Advisor.query.filter(
            Advisor.username == new_username,
            Advisor.id != user_id
        ).first()
        
        if existing_username:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check if email already exists (excluding current user)
        existing_email = Advisor.query.filter(
            Advisor.email == new_email,
            Advisor.id != user_id
        ).first()
        
        if existing_email:
            return jsonify({'error': 'Email already exists'}), 400
        
        try:
            # Update credentials
            advisor.email = new_email
            advisor.username = new_username
            
            # Update password if provided
            if new_password:
                from werkzeug.security import generate_password_hash
                advisor.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully updated credentials for {advisor.full_name}'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to update credentials: {str(e)}'}), 500

    def reset_user_password(self):
        """Reset user's password to a default value"""
        data = request.get_json()
        user_id = data.get('user_id')
        new_password = data.get('password', 'password123')  # Default password
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        advisor = db.session.get(Advisor, user_id)
        if not advisor:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            from werkzeug.security import generate_password_hash
            advisor.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Password reset for {advisor.full_name}',
                'new_password': new_password
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500

    def get_user_details(self, user_id):
        """Get user details for editing"""
        advisor = db.session.get(Advisor, user_id)
        if not advisor:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'id': advisor.id,
            'full_name': advisor.full_name,
            'username': advisor.username,
            'email': advisor.email,
            'is_master': advisor.is_master
        })

    def debug_referrals(self):
        """Debug endpoint to check referral data"""
        current_company = SessionManager.get_current_company(session)
        
        # Import Submission model
        from app.models.submission import Submission
        
        # Get all submissions for debugging
        all_submissions = Submission.query.filter_by(company=current_company).all()
        
        # Get referral submissions
        referral_submissions = [s for s in all_submissions if s.business_type and 'referral' in s.business_type.lower()]
        
        # Get current user's submissions  
        user = self.get_current_user()
        user_submissions = [s for s in all_submissions if s.advisor_name == user.full_name]
        user_referrals = [s for s in user_submissions if s.business_type and 'referral' in s.business_type.lower()]
        
        # Get all unique business types
        business_types = list(set([s.business_type for s in all_submissions]))
        
        debug_data = {
            'total_submissions': len(all_submissions),
            'referral_submissions_count': len(referral_submissions),
            'user_submissions_count': len(user_submissions), 
            'user_referrals_count': len(user_referrals),
            'all_business_types': business_types,
            'referral_submissions': [
                {
                    'advisor_name': s.advisor_name,
                    'business_type': s.business_type,
                    'referral_to': s.referral_to,
                    'customer_name': s.customer_name,
                    'date': s.submission_date.strftime('%Y-%m-%d')
                } for s in referral_submissions
            ],
            'user_referrals': [
                {
                    'business_type': s.business_type,
                    'referral_to': s.referral_to,
                    'customer_name': s.customer_name,
                    'date': s.submission_date.strftime('%Y-%m-%d')
                } for s in user_referrals
            ]
        }
        
        return jsonify(debug_data)
    
    def debug_dashboard_calculation(self):
        """Debug the actual dashboard calculation"""
        user = self.get_current_user()
        current_company = SessionManager.get_current_company(session)
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date, end_date = DateService.resolve_period_dates(period, start_str, end_str)
        
        # Get the same data the dashboard uses
        metrics = user.calculate_metrics_for_period(
            current_company, start_date, end_date,
            config_manager.get_valid_business_types(current_company),
            config_manager.get_valid_paid_case_types(current_company)
        )
        
        # Debug referrals received calculation
        referrals_received = 0
        matching_referrals = []
        is_recipient = ReferralRecipient.is_referral_recipient(user.id, current_company)
        
        if is_recipient:
            from app.models.submission import Submission
            all_referrals = Submission.query.filter(
                Submission.company == current_company,
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.business_type == 'Referral'
            ).all()
            
            for referral in all_referrals:
                if self._check_referral_match(referral.referral_to, user.full_name):
                    referrals_received += 1
                    matching_referrals.append({
                        'customer_name': referral.customer_name,
                        'advisor_name': referral.advisor_name,
                        'referral_to': referral.referral_to,
                        'date': referral.submission_date.strftime('%Y-%m-%d')
                    })
        
        # Get user's raw submissions for the period (referrals MADE by this user)
        user_submissions = user.get_submissions_for_period(current_company, start_date, end_date)
        user_referrals = [s for s in user_submissions if s.business_type == 'Referral']
        
        debug_data = {
            'user': user.full_name,
            'company': current_company,
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'is_referral_recipient': is_recipient,
            'calculated_metrics': metrics,
            'referrals_received_calculated': referrals_received,
            'matching_referrals': matching_referrals,
            'user_referrals_made_in_period': len(user_referrals),
            'user_referrals_made_details': [
                {
                    'customer_name': r.customer_name,
                    'referral_to': r.referral_to,
                    'date': r.submission_date.strftime('%Y-%m-%d')
                } for r in user_referrals
            ],
            'name_mappings': self._get_referral_name_mappings(),
            'valid_business_types': config_manager.get_valid_business_types(current_company)
        }
        
        return jsonify(debug_data)

    def get_performance_boxplot(self):
        """Get box plot performance data for current user"""
        user = self.get_current_user()
        if not user:
            return jsonify({'periods': [], 'values': [], 'monthly_goals': [], 'current_total': 0, 'monthly_goal': 0})

        current_company = SessionManager.get_current_company(session)
        metric_type = request.args.get('type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        analytics_service = AnalyticsService(current_company)
        boxplot_data = analytics_service.get_advisor_performance_boxplot(
            user, period, metric_type, start_str, end_str
        )
        
        return jsonify(boxplot_data)

    def get_advisor_performance_boxplot(self, advisor_id):
        """Get box plot performance data for a specific advisor (master only)"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return jsonify({'periods': [], 'values': [], 'monthly_goals': [], 'current_total': 0, 'monthly_goal': 0})

        current_company = SessionManager.get_current_company(session)
        metric_type = request.args.get('type', 'submitted')
        period = request.args.get('period', 'month')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        analytics_service = AnalyticsService(current_company)
        boxplot_data = analytics_service.get_advisor_performance_boxplot(
            advisor, period, metric_type, start_str, end_str
        )
        
        return jsonify(boxplot_data)
    
    def advisor_sync(self):
        """Sync data for regular advisors (not master restricted)"""
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
        

    def debug_all_referrals(self):
        """Debug endpoint to see all referral data"""
        current_company = SessionManager.get_current_company(session)
        
        from app.models.submission import Submission
        
        # Get all referrals in the system
        all_referrals = Submission.query.filter(
            Submission.company == current_company,
            Submission.business_type == 'Referral'
        ).all()
        
        # Get all referral recipients
        recipients = ReferralRecipient.get_recipients_for_company(current_company)
        
        # Get all advisors
        all_advisors = Advisor.query.all()
        
        debug_data = {
            'total_referrals_in_db': len(all_referrals),
            'total_recipients_configured': len(recipients),
            'total_advisors': len(all_advisors),
            'company': current_company,
            'all_referrals': [
                {
                    'id': r.id,
                    'advisor_name': r.advisor_name,
                    'business_type': r.business_type,
                    'referral_to': r.referral_to,
                    'customer_name': r.customer_name,
                    'date': r.submission_date.strftime('%Y-%m-%d'),
                    'company': r.company
                } for r in all_referrals
            ],
            'configured_recipients': [
                {
                    'advisor_id': rec.advisor_id,
                    'advisor_name': rec.advisor.full_name,
                    'company': rec.company,
                    'is_active': rec.is_active
                } for rec in recipients
            ],
            'all_advisors': [
                {
                    'id': adv.id,
                    'full_name': adv.full_name,
                    'is_master': adv.is_master
                } for adv in all_advisors
            ]
        }
        
        return jsonify(debug_data)