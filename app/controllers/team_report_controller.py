# app/controllers/team_report_controller.py
"""
Minimal Team Performance Report Controller - Uses existing systems
"""

from flask import request, jsonify, session
from datetime import datetime, timedelta
from app.controllers.base import BaseController
from app.config.session import SessionManager
from app.config import config_manager
from app.models.team import Team
from app.models.advisor import Advisor

class TeamReportController(BaseController):
    """Handles team performance reporting with existing data"""
    
    def register_routes(self):
        """Register team report routes"""
        
        print("Registering team report routes...")
        
        # Master-only route for team performance report
        self.app.add_url_rule('/api/teams/performance-report/<int:team_id>', 
                             'api.team_performance_report',
                             self.master_required(self.get_team_performance_report), 
                             methods=['GET'])
        
        # Get available teams for performance reports
        self.app.add_url_rule('/api/teams/performance-available', 
                             'api.teams_performance_available',
                             self.master_required(self.get_available_teams), 
                             methods=['GET'])
        
        print("Team report routes registered successfully")
    
    def get_available_teams(self):
        """Get available teams for the current company"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Access denied - Master users only'}), 403
            
            current_company = SessionManager.get_current_company(session)
            teams = Team.query.filter_by(company=current_company).all()
            
            team_list = []
            for team in teams:
                team_list.append({
                    'id': team.id,
                    'name': team.name,
                    'monthly_goal': team.monthly_goal,
                    'member_count': len(team.members),
                    'is_hidden': team.is_hidden
                })
            
            return jsonify({
                'success': True,
                'teams': team_list,
                'company': current_company
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_team_performance_report(self, team_id):
        """Generate team performance report using existing data only"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Access denied - Master users only'}), 403
            
            current_company = SessionManager.get_current_company(session)
            
            # Get the team
            team = Team.query.filter_by(id=team_id, company=current_company).first()
            if not team:
                return jsonify({'error': 'Team not found'}), 404
            
            # Parse date parameters
            month = request.args.get('month', datetime.now().strftime('%Y-%m'))
            
            try:
                report_date = datetime.strptime(month, '%Y-%m')
                start_date = report_date.replace(day=1)
                # Get last day of month
                if report_date.month == 12:
                    end_date = report_date.replace(year=report_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = report_date.replace(month=report_date.month + 1, day=1) - timedelta(days=1)
                
            except ValueError:
                return jsonify({'error': 'Invalid month format. Use YYYY-MM'}), 400
            
            # Get team members
            team_members = team.members
            if not team_members:
                return jsonify({
                    'error': 'No team members found',
                    'team_name': team.name,
                    'team_id': team.id
                })
            
            # Build basic report using existing submission system
            member_reports = []
            
            for member in team_members:
                # Get submission metrics from existing system
                submission_metrics = member.calculate_metrics_for_period(
                    current_company, start_date, end_date,
                    config_manager.get_valid_business_types(current_company),
                    config_manager.get_valid_paid_case_types(current_company)
                )
                
                # Placeholder values for non-existing integrations
                appointments_booked = 15  # Placeholder
                appointments_completed = 12  # Placeholder
                outbound_calls = 85  # Placeholder
                total_activity = outbound_calls + appointments_completed
                
                # Get application metrics from submissions
                applications = submission_metrics.get('submissions_count', 0)
                insurance_apps = self._count_business_type(member, start_date, end_date, current_company, 'insurance')
                cnc_apps = self._count_business_type(member, start_date, end_date, current_company, 'conveyancing')
                insurance_referrals = self._count_referrals(member, start_date, end_date, current_company, 'insurance')
                other_referrals = self._count_referrals(member, start_date, end_date, current_company, 'other')
                
                # Financial metrics
                submitted_amount = submission_metrics.get('expected_proc', 0)
                fees_amount = submission_metrics.get('expected_fee', 0)
                submitted_plus_fees = submitted_amount + fees_amount
                
                # Calculate conversion rate
                total_apps = applications + insurance_apps + cnc_apps
                conversion_rate = (total_apps / appointments_completed * 100) if appointments_completed > 0 else 0
                
                # Placeholder targets
                target_activity = 250
                target_submitted = 50000
                
                member_report = {
                    'advisor': member.full_name,
                    'appointments_booked': appointments_booked,
                    'appointments_completed': appointments_completed,
                    'outbound_calls': outbound_calls,
                    'total_activity': total_activity,
                    'num_of_m_apps': applications,
                    'insurance_apps': insurance_apps,
                    'cnc_apps': cnc_apps,
                    'insurance_referrals': insurance_referrals,
                    'other_referrals': other_referrals,
                    'submitted_plus_fees': submitted_plus_fees,
                    'conversion_rate': round(conversion_rate, 1),
                    'target_activity': target_activity,
                    'target_submitted': target_submitted,
                    'activity_vs_target': f"{(total_activity/target_activity*100):.0f}%" if target_activity > 0 else "N/A",
                    'submitted_vs_target': f"{(submitted_plus_fees/target_submitted*100):.0f}%" if target_submitted > 0 else "N/A"
                }
                
                member_reports.append(member_report)
            
            # Calculate team totals
            team_totals = self._calculate_team_totals(member_reports)
            
            # Sort by total activity (descending)
            member_reports.sort(key=lambda x: x['total_activity'], reverse=True)
            
            return jsonify({
                'success': True,
                'team_name': team.name,
                'team_id': team.id,
                'month': month,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'month_name': start_date.strftime('%B %Y')
                },
                'team_totals': team_totals,
                'members': member_reports,
                'data_sources': {
                    'calendly_integration': 'placeholder',
                    'call_data_source': 'placeholder',
                    'submission_data': 'database',
                    'members_analyzed': len(member_reports)
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    def _count_business_type(self, advisor, start_date, end_date, company, business_type):
        """Count submissions by business type"""
        from app.models.submission import Submission
        
        return Submission.query.filter(
            Submission.advisor_name == advisor.full_name,
            Submission.company == company,
            Submission.submission_date >= start_date,
            Submission.submission_date <= end_date,
            Submission.business_type.ilike(f'%{business_type}%')
        ).count()
    
    def _count_referrals(self, advisor, start_date, end_date, company, referral_type):
        """Count referrals by type"""
        from app.models.submission import Submission
        
        if referral_type == 'insurance':
            return Submission.query.filter(
                Submission.advisor_name == advisor.full_name,
                Submission.company == company,
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.business_type == 'Referral',
                Submission.referral_to.ilike('%insurance%')
            ).count()
        else:
            return Submission.query.filter(
                Submission.advisor_name == advisor.full_name,
                Submission.company == company,
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.business_type == 'Referral',
                ~Submission.referral_to.ilike('%insurance%')
            ).count()
    
    def _calculate_team_totals(self, member_reports):
        """Calculate team totals from member reports"""
        if not member_reports:
            return {}
        
        totals = {
            'appointments_booked': sum(m['appointments_booked'] for m in member_reports),
            'appointments_completed': sum(m['appointments_completed'] for m in member_reports),
            'outbound_calls': sum(m['outbound_calls'] for m in member_reports),
            'total_activity': sum(m['total_activity'] for m in member_reports),
            'num_of_m_apps': sum(m['num_of_m_apps'] for m in member_reports),
            'insurance_apps': sum(m['insurance_apps'] for m in member_reports),
            'cnc_apps': sum(m['cnc_apps'] for m in member_reports),
            'insurance_referrals': sum(m['insurance_referrals'] for m in member_reports),
            'other_referrals': sum(m['other_referrals'] for m in member_reports),
            'submitted_plus_fees': sum(m['submitted_plus_fees'] for m in member_reports),
            'target_activity': sum(m['target_activity'] for m in member_reports),
            'target_submitted': sum(m['target_submitted'] for m in member_reports),
        }
        
        # Calculate team conversion rate
        total_apps = totals['num_of_m_apps'] + totals['insurance_apps'] + totals['cnc_apps']
        totals['conversion_rate'] = round(
            (total_apps / totals['appointments_completed'] * 100) if totals['appointments_completed'] > 0 else 0, 
            1
        )
        
        # Calculate team vs target percentages
        totals['activity_vs_target'] = f"{(totals['total_activity']/totals['target_activity']*100):.0f}%" if totals['target_activity'] > 0 else "N/A"
        totals['submitted_vs_target'] = f"{(totals['submitted_plus_fees']/totals['target_submitted']*100):.0f}%" if totals['target_submitted'] > 0 else "N/A"
        
        return totals