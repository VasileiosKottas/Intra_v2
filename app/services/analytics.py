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
    
    def get_advisor_performance_boxplot(self, advisor, period: str, metric_type: str, start_str: str = None, end_str: str = None) -> Dict:
        """Get box plot data for an advisor with period-appropriate grouping"""
        from datetime import datetime, timedelta
        from calendar import monthrange
        import calendar
        
        start_date, end_date = self.date_service.resolve_period_dates(period, start_str, end_str)
        
        # Get advisor's yearly goal and calculate monthly goal
        yearly_goal = advisor.get_yearly_goal_for_company(self.company) or 50000.0
        monthly_goal = yearly_goal / 12
        
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
        
        # Choose data source
        data_by_date = subs_by_date if metric_type == 'submitted' else paid_by_date
        
        periods = []
        values = []
        monthly_goals = []
        
        if period == 'month':
            # Weekly grouping for month view
            current_date = start_date
            week_start = start_date
            
            while current_date <= end_date:
                # Find week end (Sunday or end_date)
                week_end = min(week_start + timedelta(days=6), end_date)
                
                # Sum values for this week
                week_total = 0.0
                check_date = week_start
                while check_date <= week_end:
                    week_total += data_by_date.get(check_date, 0.0)
                    check_date += timedelta(days=1)
                
                # Format week label
                if week_start == week_end:
                    week_label = week_start.strftime('%b %d')
                else:
                    week_label = f"{week_start.strftime('%b %d')} - {week_end.strftime('%d')}"
                
                periods.append(week_label)
                values.append(round(week_total, 2))
                # Weekly goal is monthly goal / ~4.3 weeks
                weekly_goal = monthly_goal / 4.3
                monthly_goals.append(round(weekly_goal, 2))
                
                # Move to next week
                week_start = week_end + timedelta(days=1)
                current_date = week_start
        
        else:
            # Monthly grouping for quarter, year, and custom
            current_date = start_date.replace(day=1)  # Start from first day of month
            
            while current_date <= end_date:
                # Get last day of current month
                last_day = monthrange(current_date.year, current_date.month)[1]
                month_end = current_date.replace(day=last_day)
                
                # Don't go beyond end_date
                month_end = min(month_end, end_date)
                
                # Sum values for this month
                month_total = 0.0
                check_date = current_date
                while check_date <= month_end:
                    month_total += data_by_date.get(check_date, 0.0)
                    check_date += timedelta(days=1)
                
                # Format month label
                month_label = current_date.strftime('%b %Y')
                
                periods.append(month_label)
                values.append(round(month_total, 2))
                monthly_goals.append(round(monthly_goal, 2))
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculate current total (cumulative)
        current_total = sum(values)
        
        return {
            'periods': periods,
            'values': values,
            'monthly_goals': monthly_goals,
            'current_total': current_total,
            'monthly_goal': monthly_goal
        }