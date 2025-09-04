# app/services/scheduler_service.py
"""
Automated email report scheduler for weekly team reports
"""

import schedule
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from app.services.email_service import SMTPEmailService
import os

logger = logging.getLogger(__name__)

class EmailReportScheduler:
    """Manages automated weekly email report scheduling"""
    
    def __init__(self):
        self.email_service = None
        self.is_running = False
        self.scheduler_thread = None
        self.enabled_teams = {}  # Store team email configurations
        
        # Initialize email service from environment variables
        self._initialize_email_service()
        
    def _initialize_email_service(self):
        """Initialize SMTP email service from environment variables"""
        try:
            self.email_service = SMTPEmailService.from_env()
            logger.info("SMTP email service initialized successfully")
            
        except ValueError as e:
            logger.warning(f"SMTP credentials not configured: {e}")
            logger.info("Set SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD to enable automated emails")
            
        except Exception as e:
            logger.error(f"Failed to initialize SMTP email service: {e}")
    
    def configure_team_emails(self, team_configs: Dict):
        """
        Configure email settings for teams
        
        team_configs format:
        {
            team_id: {
                'enabled': True,
                'sender_email': 'reports@company.com',
                'recipient_emails': ['team@company.com', 'manager@company.com'],
                'send_day': 'monday',  # Day of month to send monthly reports
                'send_time': '09:00'   # 24-hour format
            }
        }
        """
        self.enabled_teams = team_configs
        self._setup_schedules()
        logger.info(f"Configured monthly email schedules for {len(team_configs)} teams")
    
    def add_team_email_config(self, team_id: int, config: Dict):
        """Add or update email configuration for a specific team"""
        self.enabled_teams[team_id] = config
        self._setup_schedules()
        logger.info(f"Updated email configuration for team {team_id}")
    
    def remove_team_email_config(self, team_id: int):
        """Remove email configuration for a team"""
        if team_id in self.enabled_teams:
            del self.enabled_teams[team_id]
            self._setup_schedules()
            logger.info(f"Removed email configuration for team {team_id}")
    
    def _setup_schedules(self):
        """Setup scheduled jobs based on team configurations"""
        # Clear existing schedules
        schedule.clear()
        
        if not self.email_service:
            logger.warning("Email service not available, skipping schedule setup")
            return
        
        # Group teams by schedule (day + time)
        schedule_groups = {}
        
        for team_id, config in self.enabled_teams.items():
            if not config.get('enabled', False):
                continue
                
            day = config.get('send_day', 'monday').lower()
            time_str = config.get('send_time', '09:00')
            
            schedule_key = f"{day}_{time_str}"
            
            if schedule_key not in schedule_groups:
                schedule_groups[schedule_key] = []
                
            schedule_groups[schedule_key].append(team_id)
        
        # Create scheduled jobs
        for schedule_key, team_ids in schedule_groups.items():
            day, time_str = schedule_key.split('_')
            
            # Map day names to schedule methods
            day_map = {
                'monday': schedule.every().monday,
                'tuesday': schedule.every().tuesday,
                'wednesday': schedule.every().wednesday,
                'thursday': schedule.every().thursday,
                'friday': schedule.every().friday,
                'saturday': schedule.every().saturday,
                'sunday': schedule.every().sunday
            }
            
            if day in day_map:
                job = day_map[day].at(time_str).do(self._send_scheduled_reports, team_ids)
                logger.info(f"Scheduled monthly reports for teams {team_ids} every {day} at {time_str}")
    
    def _send_scheduled_reports(self, team_ids: List[int]):
        """Send monthly reports for scheduled teams"""
        logger.info(f"Starting scheduled monthly email reports for teams: {team_ids}")
        
        success_count = 0
        error_count = 0
        
        for team_id in team_ids:
            try:
                config = self.enabled_teams.get(team_id)
                if not config:
                    logger.warning(f"No configuration found for team {team_id}")
                    continue
                
                # Import here to avoid circular imports
                from flask import current_app
                
                with current_app.app_context():
                    # Get team from database
                    from app.models.team import Team
                    team = Team.query.get(team_id)
                    
                    if not team:
                        logger.error(f"Team {team_id} not found in database")
                        error_count += 1
                        continue
                    
                    # Send the email
                    success = self.email_service.send_team_report_email(
                        sender_email=config['sender_email'],
                        recipient_emails=config['recipient_emails'],
                        team_id=team_id,
                        team_name=team.name
                    )
                    
                    if success:
                        success_count += 1
                        logger.info(f"Successfully sent report for team: {team.name}")
                    else:
                        error_count += 1
                        logger.error(f"Failed to send report for team: {team.name}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing team {team_id}: {e}")
        
        logger.info(f"Scheduled reports completed. Success: {success_count}, Errors: {error_count}")
    
    def send_test_email(self, team_id: int) -> bool:
        """Send a test email for a specific team"""
        if not self.email_service:
            logger.error("Email service not available")
            return False
            
        config = self.enabled_teams.get(team_id)
        if not config:
            logger.error(f"No email configuration found for team {team_id}")
            return False
        
        try:
            # Import here to avoid circular imports
            from flask import current_app
            
            with current_app.app_context():
                from app.models.team import Team
                team = Team.query.get(team_id)
                
                if not team:
                    logger.error(f"Team {team_id} not found")
                    return False
                
                # Send with test subject
                success = self.email_service.send_team_report_email(
                    sender_email=config['sender_email'],
                    recipient_emails=config['recipient_emails'],
                    team_id=team_id,
                    team_name=team.name,
                    subject_override=f"🧪 TEST - {team.name} Performance Report"
                )
                
                if success:
                    logger.info(f"Test email sent successfully for team: {team.name}")
                else:
                    logger.error(f"Test email failed for team: {team.name}")
                    
                return success
                
        except Exception as e:
            logger.error(f"Error sending test email for team {team_id}: {e}")
            return False
    
    def start_scheduler(self):
        """Start the background scheduler thread"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        if not self.email_service:
            logger.warning("Email service not available, scheduler not started")
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Email report scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        logger.info("Email report scheduler stopped")
    
    def _run_scheduler(self):
        """Background thread that runs the scheduler"""
        logger.info("Scheduler thread started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
        
        logger.info("Scheduler thread stopped")
    
    def get_next_run_times(self) -> Dict:
        """Get next scheduled run times for all configured teams"""
        next_runs = {}
        
        for job in schedule.get_jobs():
            # Extract team info from job (this is a simplified approach)
            job_info = {
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'job_func': str(job.job_func),
                'interval': str(job.start_day) if hasattr(job, 'start_day') else 'Unknown'
            }
            next_runs[str(job)] = job_info
        
        return next_runs
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'email_service_available': self.email_service is not None,
            'configured_teams': len(self.enabled_teams),
            'active_schedules': len(schedule.get_jobs()),
            'enabled_teams': list(self.enabled_teams.keys())
        }

# Global scheduler instance
report_scheduler = EmailReportScheduler()