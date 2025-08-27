"""
Data integrity checking service
"""
from app.models import db 
from app.models.submission import Submission
from app.models.paid_case import PaidCase
from app.models.sync_log import SyncLog
from datetime import datetime, timedelta

class IntegrityCheckService:
    """Service for checking data integrity and consistency"""
    
    def __init__(self, company: str):
        self.company = company
    
    def run_full_check(self) -> int:
        """Run comprehensive integrity check"""
        issues_found = 0
        
        # Check for missing advisor assignments
        issues_found += self._check_missing_advisor_assignments()
        
        # Check for duplicate entries
        issues_found += self._check_duplicate_entries()
        
        # Check for data consistency
        issues_found += self._check_data_consistency()
        
        # Check for webhook delivery failures
        issues_found += self._check_webhook_gaps()
        
        return issues_found
    
    def _check_missing_advisor_assignments(self) -> int:
        """Check for submissions/cases with missing advisor assignments"""
        missing_advisors = 0
        
        # Check submissions
        submissions_without_advisor = Submission.query.filter(
            Submission.company == self.company,
            Submission.advisor_id.is_(None),
            Submission.advisor_name.isnot(None)
        ).all()
        
        missing_advisors += len(submissions_without_advisor)
        
        # Check paid cases
        cases_without_advisor = PaidCase.query.filter(
            PaidCase.company == self.company,
            PaidCase.advisor_id.is_(None),
            PaidCase.advisor_name.isnot(None)
        ).all()
        
        missing_advisors += len(cases_without_advisor)
        
        if missing_advisors > 0:
            print(f"Found {missing_advisors} records with missing advisor assignments for {self.company}")
        
        return missing_advisors
    
    def _check_duplicate_entries(self) -> int:
        """Check for potential duplicate entries"""
        duplicates = 0
        
        # Check for duplicate JotForm IDs (shouldn't happen but worth checking)
        submission_duplicates = db.session.query(
            Submission.jotform_id, db.func.count(Submission.jotform_id)
        ).filter(
            Submission.company == self.company
        ).group_by(Submission.jotform_id).having(db.func.count(Submission.jotform_id) > 1).all()
        
        duplicates += len(submission_duplicates)
        
        paid_case_duplicates = db.session.query(
            PaidCase.jotform_id, db.func.count(PaidCase.jotform_id)
        ).filter(
            PaidCase.company == self.company
        ).group_by(PaidCase.jotform_id).having(db.func.count(PaidCase.jotform_id) > 1).all()
        
        duplicates += len(paid_case_duplicates)
        
        if duplicates > 0:
            print(f"Found {duplicates} duplicate entries for {self.company}")
        
        return duplicates
    
    def _check_data_consistency(self) -> int:
        """Check for data consistency issues"""
        issues = 0
        
        # Check for submissions with zero values when they shouldn't be
        zero_value_submissions = Submission.query.filter(
            Submission.company == self.company,
            Submission.expected_proc == 0,
            Submission.expected_fee == 0,
            Submission.business_type != 'Referral'  # Referrals can have zero values
        ).count()
        
        if zero_value_submissions > 0:
            print(f"Found {zero_value_submissions} non-referral submissions with zero values for {self.company}")
            issues += zero_value_submissions
        
        # Check for paid cases with zero values
        zero_value_cases = PaidCase.query.filter(
            PaidCase.company == self.company,
            PaidCase.value == 0
        ).count()
        
        if zero_value_cases > 0:
            print(f"Found {zero_value_cases} paid cases with zero values for {self.company}")
            issues += zero_value_cases
        
        return issues
    
    def _check_webhook_gaps(self) -> int:
        """Check for potential webhook delivery gaps"""
        # This is a heuristic check - look for time periods where we got no data
        # but historically we usually get data
        
        # Check last 7 days for unusual gaps
        week_ago = datetime.now().date() - timedelta(days=7)
        
        recent_submissions = Submission.query.filter(
            Submission.company == self.company,
            Submission.submission_date >= week_ago
        ).count()
        
        recent_paid_cases = PaidCase.query.filter(
            PaidCase.company == self.company,
            PaidCase.date_paid >= week_ago
        ).count()
        
        # Simple heuristic: if we got very little data this week compared to historical average
        # This would need more sophisticated logic based on your business patterns
        
        return 0  # Placeholder for now