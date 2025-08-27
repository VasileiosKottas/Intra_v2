"""
Data synchronization services
"""

import schedule
import time
import threading
from datetime import datetime
from typing import Tuple
from app.models import db
from app.models.advisor import Advisor
from app.models.submission import Submission
from app.models.paid_case import PaidCase
from app.models.sync_log import SyncLog
from app.services.jotform import JotFormService
from app.config import config_manager

class DataSyncService:
    """Service for synchronizing data from JotForm"""
    
    def __init__(self, company: str):
        self.company = company
        self.jotform_service = JotFormService(company)
    
    def sync_submissions(self) -> int:
        """Sync submissions for the company"""
        submissions = self.jotform_service.process_submissions()
        submissions_added = 0
        
        for submission_data in submissions:
            try:
                existing = Submission.query.filter_by(jotform_id=submission_data['jotform_id']).first()
                if not existing:
                    advisor = Advisor.query.filter_by(
                        full_name=submission_data['advisor_name']
                    ).first()
                    
                    submission = Submission(
                        advisor_name=submission_data['advisor_name'],
                        advisor_id=advisor.id if advisor else None,
                        business_type=submission_data['business_type'],
                        submission_date=submission_data['submission_date'],
                        customer_name=submission_data['customer_name'],
                        expected_proc=submission_data['expected_proc'],
                        expected_fee=submission_data['expected_fee'],
                        referral_to=submission_data['referral_to'],
                        company=self.company,
                        jotform_id=submission_data['jotform_id']
                    )
                    submission.save()
                    submissions_added += 1
            except Exception as e:
                print(f" Error adding submission: {e}")
                continue
        
        return submissions_added
    
    def sync_paid_cases(self) -> int:
        """Sync paid cases for the company - ENHANCED to update existing records"""
        paid_cases = self.jotform_service.process_paid_cases()
        paid_cases_added = 0
        paid_cases_updated = 0
        
        for case_data in paid_cases:
            try:
                existing = PaidCase.query.filter_by(jotform_id=case_data['jotform_id']).first()
                
                if not existing:
                    # Create new paid case
                    advisor = Advisor.query.filter_by(
                        full_name=case_data['advisor_name']
                    ).first()
                    
                    paid_case = PaidCase(
                        advisor_name=case_data['advisor_name'],
                        advisor_id=advisor.id if advisor else None,
                        customer_name=case_data['customer_name'],
                        case_type=case_data['case_type'],
                        value=case_data['value'],
                        date_paid=case_data['date_paid'],
                        who_referred=case_data.get('who_referred'),  # Include who_referred
                        company=self.company,
                        jotform_id=case_data['jotform_id']
                    )
                    paid_case.save()
                    paid_cases_added += 1
                
                else:
                    # Update existing record if who_referred is missing or different
                    needs_update = False
                    
                    new_who_referred = case_data.get('who_referred', '').strip()
                    current_who_referred = (existing.who_referred or '').strip()
                    
                    if new_who_referred != current_who_referred:
                        existing.who_referred = new_who_referred
                        needs_update = True
                    
                    if needs_update:
                        db.session.commit()
                        paid_cases_updated += 1
                        
            except Exception as e:
                print(f"❌ Error processing paid case: {e}")
                continue
        
        print(f"✅ Sync completed: {paid_cases_added} new cases, {paid_cases_updated} updated cases")
        return paid_cases_added
    
    def perform_sync(self) -> Tuple[int, int, bool, str]:
        """Perform full sync for the company"""
        try:
            submissions_added = self.sync_submissions()
            paid_cases_added = self.sync_paid_cases()
            
            # Log the sync
            sync_log = SyncLog(
                submissions_synced=submissions_added,
                paid_cases_synced=paid_cases_added,
                status='success',
                company=self.company
            )
            sync_log.save()
            
            return submissions_added, paid_cases_added, True, None
            
        except Exception as e:
            # Log the error
            sync_log = SyncLog(
                status='error',
                error_message=str(e),
                company=self.company
            )
            sync_log.save()
            
            return 0, 0, False, str(e)
        

class AutoSyncManager:
    """Manages automatic synchronization with JotForm for all companies"""
    
    def __init__(self, app=None):
        self.sync_running = False
        self.app = app
        self.last_full_sync = None

    def setup_hybrid_scheduler(self):
        """Setup minimal polling as backup to webhooks"""
        # Daily full sync at 2 AM (low traffic time)
        schedule.every().day.at("02:00").do(self.backup_sync_all_companies)
        
        # Optional: Weekly deeper integrity check
        schedule.every().sunday.at("01:00").do(self.integrity_check_all_companies)
        
        print("Hybrid sync scheduler configured:")
        print("  - Daily backup sync at 2:00 AM")
        print("  - Weekly integrity check on Sundays at 1:00 AM")
        print("  - Primary data delivery via webhooks")
    
    
    def backup_sync_all_companies(self):
        """Backup sync - only fetches data newer than last webhook"""
        print("Starting daily backup sync...")
        
        for company in config_manager.get_all_companies():
            self.backup_sync_company(company)
    
    def backup_sync_company(self, company: str):
        """Backup sync for specific company with date filtering"""
        if self.sync_running:
            print(f"Sync already running for {company}, skipping backup...")
            return
        
        self.sync_running = True
        print(f"Daily backup sync for {company} at {datetime.now()}")
        
        try:
            if self.app:
                with self.app.app_context():
                    # Use modified sync service that only fetches recent data
                    sync_service = BackupSyncService(company)
                    submissions_added, paid_cases_added, success, error = sync_service.perform_backup_sync()
                    
                    if success:
                        if submissions_added > 0 or paid_cases_added > 0:
                            print(f"Backup sync found missing data for {company}! Added {submissions_added} submissions and {paid_cases_added} paid cases")
                        else:
                            print(f"Backup sync confirmed data integrity for {company}")
                    else:
                        print(f"Backup sync failed for {company}: {error}")
            else:
                print(f"Cannot backup sync {company}: No Flask app context available")
                
        except Exception as e:
            print(f"Backup sync failed for {company}: {e}")
        finally:
            self.sync_running = False

    
    def integrity_check_all_companies(self):
        """Weekly integrity check - more thorough validation"""
        print("Starting weekly integrity check...")
        
        for company in config_manager.get_all_companies():
            self.integrity_check_company(company)
    
    def integrity_check_company(self, company: str):
        """Check for data inconsistencies and missing records"""
        try:
            if self.app:
                with self.app.app_context():
                    from app.services.integrity_check_service import IntegrityCheckService
                    
                    integrity_service = IntegrityCheckService(company)
                    issues_found = integrity_service.run_full_check()
                    
                    if issues_found:
                        print(f"Integrity check found {issues_found} issues for {company}")
                    else:
                        print(f"Integrity check passed for {company}")
        except Exception as e:
            print(f"Integrity check failed for {company}: {e}")
    def sync_data_automatic(self, company: str = 'windsor'):
        """Automatic sync function for specific company"""
        if self.sync_running:
            print(" Sync already running, skipping...")
            return
        
        self.sync_running = True
        print(f"🔄 Starting automatic sync for {company} at {datetime.now()}")
        
        try:
            # CRITICAL FIX: Ensure we have Flask app context for database operations
            if self.app:
                with self.app.app_context():
                    sync_service = DataSyncService(company)
                    submissions_added, paid_cases_added, success, error = sync_service.perform_sync()
                    
                    if success:
                        print(f"✅ Auto sync completed for {company}! Added {submissions_added} submissions and {paid_cases_added} paid cases")
                    else:
                        print(f"❌ Auto sync failed for {company}: {error}")
            else:
                print(f"❌ Cannot sync {company}: No Flask app context available")
                
        except Exception as e:
            print(f"❌ Auto sync failed for {company}: {e}")
        finally:
            self.sync_running = False
    
    def sync_all_companies(self):
        """Sync data for all companies"""
        for company in config_manager.get_all_companies():
            self.sync_data_automatic(company)
    
    def setup_scheduler(self):
        """Setup the sync schedule"""
        # Schedule sync at 9 AM and 5 PM daily for all companies
        schedule.every().day.at("09:00").do(self.sync_all_companies)
        schedule.every().day.at("17:00").do(self.sync_all_companies)
        
        # Schedule sync every 30 minutes between 9 AM and 5 PM for all companies
        for hour in range(9, 17):  # 9 AM to 4:30 PM
            for minute in [30]:  # 30 minutes past each hour
                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.sync_all_companies)
        
        print("📅 Sync scheduler configured for all companies:")
        print("  - Daily at 9:00 AM and 5:00 PM")
        print("  - Every 30 minutes between 9:00 AM and 5:00 PM")
    
    def run_scheduler(self):
        """Run the scheduler in background"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


class BackupSyncService(DataSyncService):
    """Backup sync service that only fetches recent data"""
    
    def perform_backup_sync(self) -> Tuple[int, int, bool, str]:
        """Perform backup sync - only fetch data from last 48 hours"""
        try:
            from datetime import timedelta
            
            # Only sync last 48 hours to catch any missed webhooks
            cutoff_date = datetime.now().date() - timedelta(days=2)
            
            submissions_added = self.sync_recent_submissions(cutoff_date)
            paid_cases_added = self.sync_recent_paid_cases(cutoff_date)
            
            # Log the backup sync
            sync_log = SyncLog(
                submissions_synced=submissions_added,
                paid_cases_synced=paid_cases_added,
                status='backup_success',
                company=self.company
            )
            sync_log.save()
            
            return submissions_added, paid_cases_added, True, None
            
        except Exception as e:
            # Log the error
            sync_log = SyncLog(
                status='backup_error',
                error_message=str(e),
                company=self.company
            )
            sync_log.save()
            
            return 0, 0, False, str(e)
    
    def sync_recent_submissions(self, cutoff_date) -> int:
        """Sync only submissions newer than cutoff date"""
        submissions = self.jotform_service.process_submissions()
        submissions_added = 0
        
        for submission_data in submissions:
            try:
                # Skip if older than cutoff
                if submission_data['submission_date'] < cutoff_date:
                    continue
                
                existing = Submission.query.filter_by(jotform_id=submission_data['jotform_id']).first()
                if not existing:
                    advisor = Advisor.query.filter_by(
                        full_name=submission_data['advisor_name']
                    ).first()
                    
                    submission = Submission(
                        advisor_name=submission_data['advisor_name'],
                        advisor_id=advisor.id if advisor else None,
                        business_type=submission_data['business_type'],
                        submission_date=submission_data['submission_date'],
                        customer_name=submission_data['customer_name'],
                        expected_proc=submission_data['expected_proc'],
                        expected_fee=submission_data['expected_fee'],
                        referral_to=submission_data['referral_to'],
                        company=self.company,
                        jotform_id=submission_data['jotform_id']
                    )
                    submission.save()
                    submissions_added += 1
                    print(f"Backup sync found missing submission: {submission_data['jotform_id']}")
            except Exception as e:
                print(f"Error adding submission in backup: {e}")
                continue
        
        return submissions_added
    
    def sync_recent_paid_cases(self, cutoff_date) -> int:
        """Sync only paid cases newer than cutoff date"""
        paid_cases = self.jotform_service.process_paid_cases()
        paid_cases_added = 0
        
        for case_data in paid_cases:
            try:
                # Skip if older than cutoff
                if case_data['date_paid'] < cutoff_date:
                    continue
                
                existing = PaidCase.query.filter_by(jotform_id=case_data['jotform_id']).first()
                if not existing:
                    advisor = Advisor.query.filter_by(
                        full_name=case_data['advisor_name']
                    ).first()
                    
                    paid_case = PaidCase(
                        advisor_name=case_data['advisor_name'],
                        advisor_id=advisor.id if advisor else None,
                        customer_name=case_data['customer_name'],
                        case_type=case_data['case_type'],
                        value=case_data['value'],
                        date_paid=case_data['date_paid'],
                        who_referred=case_data.get('who_referred'),
                        company=self.company,
                        jotform_id=case_data['jotform_id']
                    )
                    paid_case.save()
                    paid_cases_added += 1
                    print(f"Backup sync found missing paid case: {case_data['jotform_id']}")
            except Exception as e:
                print(f"Error adding paid case in backup: {e}")
                continue
        
        return paid_cases_added
