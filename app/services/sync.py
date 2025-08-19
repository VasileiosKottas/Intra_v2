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
        """Sync paid cases for the company"""
        paid_cases = self.jotform_service.process_paid_cases()
        paid_cases_added = 0
        
        for case_data in paid_cases:
            try:
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
                        company=self.company,
                        jotform_id=case_data['jotform_id']
                    )
                    paid_case.save()
                    paid_cases_added += 1
            except Exception as e:
                print(f"❌ Error adding paid case: {e}")
                continue
        
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
    
    def __init__(self):
        self.sync_running = False
    
    def sync_data_automatic(self, company: str = 'windsor'):
        """Automatic sync function for specific company"""
        if self.sync_running:
            print(" Sync already running, skipping...")
            return
        
        self.sync_running = True
        print(f" Starting automatic sync for {company} at {datetime.now()}")
        
        try:
            sync_service = DataSyncService(company)
            submissions_added, paid_cases_added, success, error = sync_service.perform_sync()
            
            if success:
                print(f" Auto sync completed for {company}! Added {submissions_added} submissions and {paid_cases_added} paid cases")
            else:
                print(f" Auto sync failed for {company}: {error}")
                
        except Exception as e:
            print(f" Auto sync failed for {company}: {e}")
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
