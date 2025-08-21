"""
Complete fix for analytics.py - Replace the entire file content
"""

"""
Analytics and metrics calculation service
"""

from datetime import timedelta, datetime
from typing import List, Dict
from app.services.date import DateService
import calendar

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
                if metric_type == 'submitted':
                    weekly_goal = monthly_goal / 4.3
                    monthly_goals.append(round(weekly_goal, 2))
                
                # Move to next week
                week_start = week_end + timedelta(days=1)
                current_date = week_start
        
        elif period == 'quarter':
            # Bi-weekly grouping for quarter view
            current_date = start_date
            bi_week_start = start_date
            bi_week_num = 1
            
            while current_date <= end_date:
                # Find bi-week end (14 days or end_date)
                bi_week_end = min(bi_week_start + timedelta(days=13), end_date)
                
                # Sum values for this bi-week
                bi_week_total = 0.0
                check_date = bi_week_start
                while check_date <= bi_week_end:
                    bi_week_total += data_by_date.get(check_date, 0.0)
                    check_date += timedelta(days=1)
                
                # Format bi-week label
                periods.append(f"Week {bi_week_num}-{bi_week_num+1}")
                values.append(round(bi_week_total, 2))
                if metric_type == 'submitted':
                    bi_weekly_goal = monthly_goal / 2.15  # roughly 2 weeks
                    monthly_goals.append(round(bi_weekly_goal, 2))
                
                # Move to next bi-week
                bi_week_start = bi_week_end + timedelta(days=1)
                current_date = bi_week_start
                bi_week_num += 2
        
        elif period == 'year':
            # Monthly grouping for year view
            current_date = start_date.replace(day=1)  # Start from first day of month
            
            while current_date <= end_date:
                # Get last day of current month
                last_day = calendar.monthrange(current_date.year, current_date.month)[1]
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
                if metric_type == 'submitted':
                    monthly_goals.append(round(monthly_goal, 2))
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        
        else:
            # Custom period - decide grouping based on duration
            total_days = (end_date - start_date).days
            
            if total_days <= 31:
                # Daily grouping for short custom periods
                current_date = start_date
                while current_date <= end_date:
                    day_total = data_by_date.get(current_date, 0.0)
                    periods.append(current_date.strftime('%d %b'))
                    values.append(round(day_total, 2))
                    if metric_type == 'submitted':
                        daily_goal = monthly_goal / 30  # rough daily goal
                        monthly_goals.append(round(daily_goal, 2))
                    current_date += timedelta(days=1)
            
            elif total_days <= 100:
                # Weekly grouping for medium custom periods
                current_date = start_date
                week_start = start_date
                
                while current_date <= end_date:
                    week_end = min(week_start + timedelta(days=6), end_date)
                    
                    week_total = 0.0
                    check_date = week_start
                    while check_date <= week_end:
                        week_total += data_by_date.get(check_date, 0.0)
                        check_date += timedelta(days=1)
                    
                    if week_start == week_end:
                        week_label = week_start.strftime('%d %b')
                    else:
                        week_label = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
                    
                    periods.append(week_label)
                    values.append(round(week_total, 2))
                    if metric_type == 'submitted':
                        weekly_goal = monthly_goal / 4.3
                        monthly_goals.append(round(weekly_goal, 2))
                    
                    week_start = week_end + timedelta(days=1)
                    current_date = week_start
            
            else:
                # Monthly grouping for long custom periods
                current_date = start_date.replace(day=1)
                
                while current_date <= end_date:
                    last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                    month_end = current_date.replace(day=last_day)
                    month_end = min(month_end, end_date)
                    
                    month_total = 0.0
                    check_date = current_date
                    while check_date <= month_end:
                        month_total += data_by_date.get(check_date, 0.0)
                        check_date += timedelta(days=1)
                    
                    month_label = current_date.strftime('%b %Y')
                    periods.append(month_label)
                    values.append(round(month_total, 2))
                    if metric_type == 'submitted':
                        monthly_goals.append(round(monthly_goal, 2))
                    
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
        
        # Calculate current total (cumulative for the entire period)
        current_total = sum(values)
        
        # Limit to last 12 data points for chart readability
        max_points = 12
        if len(periods) > max_points:
            periods = periods[-max_points:]
            values = values[-max_points:]
            monthly_goals = monthly_goals[-max_points:] if monthly_goals else []
        
        return {
            'periods': periods,
            'values': values,
            'monthly_goals': monthly_goals,
            'current_total': current_total,
            'monthly_goal': monthly_goal
        }