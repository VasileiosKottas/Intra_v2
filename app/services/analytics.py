"""
Analytics and metrics calculation service
"""

from datetime import timedelta
from typing import List, Dict
from app.services.date import DateService

class AnalyticsService:
    """Service for analytics and metrics calculations"""
    
    def __init__(self, company: str):
        self.company = company
        from app.config import config_manager
        self.config = config_manager.get_company_config(company)
        self.date_service = DateService()
    
    def get_advisor_performance_timeline(self, advisor, period: str, metric_type: str, start_str: str = None, end_str: str = None) -> List[Dict]:
        """Get performance timeline data for an advisor"""
        start_date, end_date = self.date_service.resolve_period_dates(period, start_str, end_str)
        
        # Get submissions and paid cases
        submissions = advisor.get_submissions_for_period(
            self.company, start_date, end_date, 
            self.config.valid_business_types if self.config else []
        )
        
        paid_cases = advisor.get_paid_cases_for_period(
            self.company, start_date, end_date,
            self.config.valid_paid_case_types if self.config else []
        )
        
        # Index by date
        subs_by_date = {}
        for submission in submissions:
            date = submission.submission_date
            subs_by_date[date] = subs_by_date.get(date, 0.0) + float(submission.total_value)

        paid_by_date = {}
        for paid_case in paid_cases:
            date = paid_case.date_paid
            paid_by_date[date] = paid_by_date.get(date, 0.0) + float(paid_case.value or 0)

        # Build cumulative series
        day = start_date
        running = 0.0
        series = []
        
        while day <= end_date:
            if metric_type == 'submitted':
                added = subs_by_date.get(day, 0.0)
            else:  # paid
                added = paid_by_date.get(day, 0.0)
            
            running += added
            series.append({
                'date': day.strftime('%Y-%m-%d'),
                'value': round(running, 2)
            })
            day += timedelta(days=1)

        return series
    
    def calculate_team_performance(self, team, period: str, start_str: str = None, end_str: str = None) -> Dict:
        """Calculate team performance metrics"""
        start_date, end_date = self.date_service.resolve_period_dates(period, start_str, end_str)
        
        return team.get_team_metrics_for_period(
            start_date, end_date,
            self.config.valid_business_types if self.config else [],
            self.config.valid_paid_case_types if self.config else []
        )