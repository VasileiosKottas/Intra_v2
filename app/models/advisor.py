"""
Advisor model with enhanced OOP methods - Updated for multiple teams
"""

from sqlalchemy import or_, and_
from app.models import db
from app.models.base import BaseModel

class AdvisorGoal(BaseModel):
    """Company-specific yearly goals for advisors"""
    __tablename__ = 'advisor_goals'
    
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    yearly_goal = db.Column(db.Float, default=50000.0)
    
    # Unique constraint to prevent duplicate goals per company
    __table_args__ = (db.UniqueConstraint('advisor_id', 'company', name='unique_advisor_company_goal'),)

class Advisor(BaseModel):
    """Advisor model with enhanced OOP methods for multiple teams"""
    __tablename__ = 'advisors'
    
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_master = db.Column(db.Boolean, default=False)
    is_hidden_from_team = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    team_memberships = db.relationship('AdvisorTeam', backref='advisor', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='advisor')
    paid_cases = db.relationship('PaidCase', backref='advisor')
    yearly_goals = db.relationship('AdvisorGoal', backref='advisor', cascade='all, delete-orphan')
    
    def get_teams_for_company(self, company):
        """Get ALL teams for a specific company"""
        teams = []
        for membership in self.team_memberships:
            if membership.team.company == company:
                teams.append(membership.team)
        return teams
    
    def get_visible_team_for_company(self, company):
        """Get the visible (non-hidden) team for a specific company"""
        for membership in self.team_memberships:
            if membership.team.company == company and not membership.team.is_hidden:
                return membership.team
        return None
    
    def get_primary_team_for_company(self, company):
        """Get primary team for a company (visible team first, then any team)"""
        # First try to get a visible team
        visible_team = self.get_visible_team_for_company(company)
        if visible_team:
            return visible_team
        
        # If no visible team, return any team
        teams = self.get_teams_for_company(company)
        return teams[0] if teams else None
    
    def get_team_for_company(self, company):
        """Backward compatibility - returns primary team"""
        return self.get_primary_team_for_company(company)
    
    def is_in_hidden_team_only(self, company):
        """Check if advisor is only in hidden teams for this company"""
        teams = self.get_teams_for_company(company)
        if not teams:
            return False
        return all(team.is_hidden for team in teams)
    
    def get_yearly_goal_for_company(self, company):
        """Get yearly goal for a specific company - checks team first, then individual goal"""
        # First check if they're in a team with a goal (prefer visible teams)
        visible_team = self.get_visible_team_for_company(company)
        if visible_team:
            for membership in self.team_memberships:
                if membership.team.id == visible_team.id and membership.yearly_goal > 0:
                    return membership.yearly_goal
        
        # Then check any team goal
        for membership in self.team_memberships:
            if membership.team.company == company and membership.yearly_goal > 0:
                return membership.yearly_goal
        
        # Then check individual goal
        for goal in self.yearly_goals:
            if goal.company == company:
                return goal.yearly_goal
        
        # Default goal if none set
        return 50000.0
    
    def set_yearly_goal_for_company(self, company, goal_amount):
        """Set yearly goal for a specific company"""
        # If they're in a team, update the primary team goal
        primary_team = self.get_primary_team_for_company(company)
        
        if primary_team:
            team_membership = None
            for membership in self.team_memberships:
                if membership.team.id == primary_team.id:
                    team_membership = membership
                    break
            
            if team_membership:
                team_membership.yearly_goal = float(goal_amount)
        else:
            # Update or create individual goal
            individual_goal = None
            for goal in self.yearly_goals:
                if goal.company == company:
                    individual_goal = goal
                    break
            
            if individual_goal:
                individual_goal.yearly_goal = float(goal_amount)
            else:
                new_goal = AdvisorGoal(
                    advisor_id=self.id,
                    company=company,
                    yearly_goal=float(goal_amount)
                )
                db.session.add(new_goal)
        
        db.session.commit()
        return True
    
    def get_submissions_for_period(self, company, start_date, end_date, valid_types=None):
        """Get submissions for a specific period and company"""
        from app.models.submission import Submission
        
        query = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == company,
                or_(
                    Submission.advisor_id == self.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == self.full_name)
                )
            )
        )
        
        submissions = query.all()
        if valid_types:
            return [s for s in submissions if s.business_type in valid_types]
        return submissions
    
    def get_paid_cases_for_period(self, company, start_date, end_date, valid_types=None):
        """Get paid cases for a specific period and company"""
        from app.models.paid_case import PaidCase
        
        query = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == company,
                or_(
                    PaidCase.advisor_id == self.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == self.full_name)
                )
            )
        )
        
        cases = query.all()
        if valid_types:
            return [c for c in cases if c.case_type in valid_types]
        return cases
    
    def calculate_metrics_for_period(self, company, start_date, end_date, valid_submission_types=None, valid_case_types=None):
        """Calculate comprehensive metrics for a period"""
        submissions = self.get_submissions_for_period(company, start_date, end_date, valid_submission_types)
        paid_cases = self.get_paid_cases_for_period(company, start_date, end_date, valid_case_types)
        
        # Filter submissions for valid business types and referrals
        valid_submissions = [s for s in submissions if valid_submission_types and s.business_type in valid_submission_types]
        
        # Count referrals separately - get ALL submissions without any business type filtering
        all_user_submissions = self.get_submissions_for_period(company, start_date, end_date, None)
        referrals_made = len([s for s in all_user_submissions if s.business_type == 'Referral'])
        
        # Calculate totals
        total_submitted = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in valid_submissions)
        total_fee = sum(s.expected_fee or 0 for s in valid_submissions)
        total_paid = sum(p.value for p in paid_cases)
        
        # Calculate applications breakdown
        applications = {}
        for submission in valid_submissions:
            if submission.business_type not in applications:
                applications[submission.business_type] = 0
            applications[submission.business_type] += 1
        
        return {
            'total_submitted': total_submitted,
            'total_fee': total_fee,
            'combined_total': total_submitted,
            'total_paid': total_paid,
            'payment_percentage': (total_paid / total_submitted * 100) if total_submitted > 0 else 0,
            'applications': applications,
            'referrals_made': referrals_made,
            'submissions_count': len(valid_submissions),
            'paid_cases_count': len(paid_cases)
        }

    def is_visible_to_advisor(self, viewing_advisor):
        """Check if this advisor should be visible to another advisor"""
        if viewing_advisor.is_master:
            return True  # Masters can see everyone
        return not self.is_hidden_from_team  # Regular advisors can't see hidden ones

    def get_visible_team_members(self, company):
        """
        Get team members that this advisor can see
        Filters out advisors that are hidden from team (unless this advisor is a master)
        """
        team = self.get_team_for_company(company)
        if not team:
            return []
        
        visible_members = []
        for member in team.members:
            if member.is_visible_to_advisor(self):
                visible_members.append(member)
        
        return visible_members