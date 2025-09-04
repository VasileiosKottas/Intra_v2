# app/controllers/email_config_controller.py
"""
Controller for managing automated email report configurations
"""

from flask import request, jsonify, render_template, session, redirect, url_for
from app.controllers.base import BaseController
from app.config.session import SessionManager
from app.services.scheduler_service import report_scheduler
from app.models.team import Team

import logging

logger = logging.getLogger(__name__)

class EmailConfigController(BaseController):
    """Handles email configuration for automated reports"""
    
    def register_routes(self):
        """Register email configuration routes"""
        try:
            # Master-only routes for email configuration
            self.app.add_url_rule('/master/email-config', 'master.email_config', 
                                self.email_config_page, methods=['GET'])
            
            # API routes with unique endpoint names
            self.app.add_url_rule('/api/email-config/teams', 'api.email_config_teams',
                                self.get_email_enabled_teams, methods=['GET'])
            
            self.app.add_url_rule('/api/email-config/team/<int:team_id>', 'api.email_config_team',
                                self.manage_team_email_config, methods=['GET', 'POST', 'DELETE'])
            
            self.app.add_url_rule('/api/email-config/test/<int:team_id>', 'api.email_config_test',
                                self.send_test_email, methods=['POST'])
            
            self.app.add_url_rule('/api/email-config/scheduler/status', 'api.email_scheduler_status',
                                self.get_scheduler_status, methods=['GET'])
            
            self.app.add_url_rule('/api/email-config/scheduler/start', 'api.email_start_scheduler',
                                self.start_scheduler, methods=['POST'])
            
            self.app.add_url_rule('/api/email-config/scheduler/stop', 'api.email_stop_scheduler',
                                self.stop_scheduler, methods=['POST'])
            
            logger.info("Email configuration routes registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering email config routes: {e}")
    
    def email_config_page(self):
        """Serve the email configuration page (master only)"""
        user = self.get_current_user()
        if not user or not user.is_master:
            return redirect(url_for('master.index'))
        
        current_company = SessionManager.get_current_company(session)
        
        # Get all teams for the current company
        from app.models.team import Team
        teams = Team.query.filter_by(company=current_company).all()
        
        return render_template('email_config.html', 
                             user=user, 
                             teams=teams,
                             current_company=current_company)
    
    def get_email_enabled_teams(self):
        """Get list of teams with email configuration"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            current_company = SessionManager.get_current_company(session)
            from app.models.team import Team
            teams = Team.query.filter_by(company=current_company).all()
            
            team_configs = []
            for team in teams:
                # Get email configuration from scheduler
                config = report_scheduler.enabled_teams.get(team.id, {})
                
                team_data = {
                    'team_id': team.id,
                    'team_name': team.name,
                    'member_count': len(team.members),
                    'monthly_goal': float(team.monthly_goal),
                    'email_enabled': config.get('enabled', False),
                    'sender_email': config.get('sender_email', ''),
                    'recipient_emails': config.get('recipient_emails', []),
                    'send_day': config.get('send_day', 'monday'),
                    'send_time': config.get('send_time', '09:00')
                }
                team_configs.append(team_data)
            
            return jsonify({
                'teams': team_configs,
                'scheduler_status': report_scheduler.get_scheduler_status()
            })
            
        except Exception as e:
            logger.error(f"Error getting email enabled teams: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _check_team_has_data(self, team):
        """Check if team has any submission or activity data"""
        try:
            from app.models.submission import Submission
            from app.models.paid_case import PaidCase
            from datetime import datetime, timedelta
            
            # Check last 30 days for recent activity
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Check for submissions
            team_member_ids = [member.id for member in team.members]
            if team_member_ids:
                recent_submissions = Submission.query.filter(
                    Submission.advisor_id.in_(team_member_ids),
                    Submission.company == team.company,
                    Submission.submission_date >= cutoff_date
                ).first()
                
                if recent_submissions:
                    return True
                
                # Check for paid cases
                recent_paid = PaidCase.query.filter(
                    PaidCase.advisor_id.in_(team_member_ids),
                    PaidCase.company == team.company,
                    PaidCase.date_paid >= cutoff_date
                ).first()
                
                return recent_paid is not None
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking team data for team {team.id}: {e}")
            return False
    
    def _get_team_last_activity(self, team):
        """Get the last activity date for the team"""
        try:
            from app.models.submission import Submission
            from app.models.paid_case import PaidCase
            from sqlalchemy import func
            
            team_member_ids = [member.id for member in team.members]
            if not team_member_ids:
                return None
            
            # Get latest submission date
            latest_submission = Submission.query.filter(
                Submission.advisor_id.in_(team_member_ids),
                Submission.company == team.company
            ).order_by(Submission.submission_date.desc()).first()
            
            # Get latest paid case date  
            latest_paid = PaidCase.query.filter(
                PaidCase.advisor_id.in_(team_member_ids),
                PaidCase.company == team.company
            ).order_by(PaidCase.date_paid.desc()).first()
            
            dates = []
            if latest_submission:
                dates.append(latest_submission.submission_date)
            if latest_paid:
                dates.append(latest_paid.date_paid)
            
            if dates:
                return max(dates).strftime('%Y-%m-%d')
            return None
            
        except Exception as e:
            logger.warning(f"Error getting last activity for team {team.id}: {e}")
            return None
    
    def manage_team_email_config(self, team_id):
        """Manage email configuration for a specific team"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            from app.models.team import Team
            from app.models.team import Team
            current_company = SessionManager.get_current_company(session)
            team = Team.query.filter_by(id=team_id, company=current_company).first()
            
            if not team:
                return jsonify({'error': 'Team not found'}), 404
            
            if request.method == 'GET':
                # Return current configuration
                config = report_scheduler.enabled_teams.get(team_id, {})
                return jsonify({
                    'team_id': team_id,
                    'team_name': team.name,
                    'config': config
                })
            
            elif request.method == 'POST':
                # Update configuration
                data = request.get_json()
                
                # Validate required fields
                if data.get('enabled') and not all([
                    data.get('sender_email'),
                    data.get('recipient_emails'),
                    data.get('send_day'),
                    data.get('send_time')
                ]):
                    return jsonify({'error': 'Missing required fields for enabled configuration'}), 400
                
                # Validate email formats (basic validation)
                if data.get('sender_email') and '@' not in data.get('sender_email'):
                    return jsonify({'error': 'Invalid sender email format'}), 400
                
                recipient_emails = data.get('recipient_emails', [])
                if isinstance(recipient_emails, str):
                    recipient_emails = [email.strip() for email in recipient_emails.split(',')]
                
                for email in recipient_emails:
                    if email and '@' not in email:
                        return jsonify({'error': f'Invalid recipient email format: {email}'}), 400
                
                # Validate day and time
                valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if data.get('send_day') and data.get('send_day').lower() not in valid_days:
                    return jsonify({'error': 'Invalid send day'}), 400
                
                try:
                    from datetime import datetime
                    datetime.strptime(data.get('send_time', '09:00'), '%H:%M')
                except ValueError:
                    return jsonify({'error': 'Invalid time format (use HH:MM)'}), 400
                
                # Create configuration
                config = {
                    'enabled': data.get('enabled', False),
                    'sender_email': data.get('sender_email', ''),
                    'recipient_emails': recipient_emails,
                    'send_day': data.get('send_day', 'monday').lower(),
                    'send_time': data.get('send_time', '09:00')
                }
                
                # Update scheduler configuration
                report_scheduler.add_team_email_config(team_id, config)
                
                return jsonify({
                    'success': True,
                    'message': f'Email configuration updated for {team.name}',
                    'config': config
                })
            
            elif request.method == 'DELETE':
                # Remove configuration
                report_scheduler.remove_team_email_config(team_id)
                return jsonify({
                    'success': True,
                    'message': f'Email configuration removed for {team.name}'
                })
            
        except Exception as e:
            logger.error(f"Error managing team email config: {e}")
            return jsonify({'error': str(e)}), 500
    
    def send_test_email(self, team_id):
        """Send a test email for a specific team"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            current_company = SessionManager.get_current_company(session)
            team = Team.query.filter_by(id=team_id, company=current_company).first()
            
            if not team:
                return jsonify({'error': 'Team not found'}), 404
            
            # Check if team has email configuration
            if team_id not in report_scheduler.enabled_teams:
                return jsonify({'error': 'No email configuration found for this team'}), 400
            
            # Send test email
            success = report_scheduler.send_test_email(team_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Test email sent successfully for {team.name}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to send test email. Check logs for details.'
                }), 500
                
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return jsonify({'error': str(e)}), 500
    
    def get_scheduler_status(self):
        """Get current scheduler status and next run times"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            status = report_scheduler.get_scheduler_status()
            next_runs = report_scheduler.get_next_run_times()
            
            return jsonify({
                'status': status,
                'next_runs': next_runs,
                'enabled_teams_details': {
                    team_id: {
                        'team_name': Team.query.get(team_id).name if Team.query.get(team_id) else 'Unknown',
                        'config': config
                    }
                    for team_id, config in report_scheduler.enabled_teams.items()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return jsonify({'error': str(e)}), 500
    
    def start_scheduler(self):
        """Start the email report scheduler"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            report_scheduler.start_scheduler()
            
            return jsonify({
                'success': True,
                'message': 'Email report scheduler started',
                'status': report_scheduler.get_scheduler_status()
            })
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return jsonify({'error': str(e)}), 500
    
    def stop_scheduler(self):
        """Stop the email report scheduler"""
        try:
            user = self.get_current_user()
            if not user or not user.is_master:
                return jsonify({'error': 'Unauthorized'}), 403
            
            report_scheduler.stop_scheduler()
            
            return jsonify({
                'success': True,
                'message': 'Email report scheduler stopped',
                'status': report_scheduler.get_scheduler_status()
            })
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            return jsonify({'error': str(e)}), 500