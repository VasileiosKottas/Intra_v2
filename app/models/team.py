"""
Team and AdvisorTeam models
"""

from app.models import db
from app.models.base import BaseModel

class AdvisorTeam(BaseModel):
    """Many-to-many relationship between Advisors and Teams"""
    __tablename__ = 'advisor_teams'
    
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    yearly_goal = db.Column(db.Float, default=0.0)
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('advisor_id', 'team_id', name='unique_advisor_team'),)

class Team(BaseModel):
    """Team model with enhanced methods"""
    __tablename__ = 'teams'
    
    name = db.Column(db.String(100), nullable=False)
    monthly_goal = db.Column(db.Float, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), default='windsor')
    is_hidden = db.Column(db.Boolean, default=False)
    
    # Relationships
    creator = db.relationship('Advisor', foreign_keys=[created_by])

    advisor_memberships = db.relationship('AdvisorTeam', backref='team', cascade='all, delete-orphan')
    
    @property
    def members(self):
        """Get all advisors in this team"""
        return [membership.advisor for membership in self.advisor_memberships]
    
    def add_member(self, advisor, yearly_goal=0.0):
        """Add a member to the team"""
        # Check if already a member
        existing = AdvisorTeam.query.filter_by(
            advisor_id=advisor.id,
            team_id=self.id
        ).first()
        
        if existing:
            return False, "Advisor already in team"
        
        # Remove from any existing team in this company
        for membership in advisor.team_memberships:
            if membership.team.company == self.company:
                db.session.delete(membership)
        
        # Add to this team
        new_membership = AdvisorTeam(
            advisor_id=advisor.id,
            team_id=self.id,
            yearly_goal=yearly_goal
        )
        db.session.add(new_membership)
        db.session.commit()
        return True, "Member added successfully"
    
    def remove_member(self, advisor):
        """Remove a member from the team"""
        membership = AdvisorTeam.query.filter_by(
            advisor_id=advisor.id,
            team_id=self.id
        ).first()
        
        if membership:
            db.session.delete(membership)
            db.session.commit()
            return True, "Member removed successfully"
        return False, "Member not found in team"
    
    def get_team_metrics_for_period(self, start_date, end_date, valid_submission_types=None, valid_case_types=None):
        """Calculate team metrics for a specific period"""
        team_metrics = {
            'total_submitted': 0,
            'total_paid': 0,
            'member_data': []
        }
        
        for member in self.members:
            member_metrics = member.calculate_metrics_for_period(
                self.company, start_date, end_date, 
                valid_submission_types, valid_case_types
            )
            
            team_metrics['total_submitted'] += member_metrics['total_submitted']
            team_metrics['total_paid'] += member_metrics['total_paid']
            
            team_metrics['member_data'].append({
                'name': member.full_name,
                'total_submitted': member_metrics['total_submitted'],
                'total_paid': member_metrics['total_paid'],
                'avg_case_size': (member_metrics['total_paid'] / member_metrics['paid_cases_count']) if member_metrics['paid_cases_count'] > 0 else 0,
                'goal_progress': (member_metrics['total_submitted'] / member.get_yearly_goal_for_company(self.company) * 100) if member.get_yearly_goal_for_company(self.company) > 0 else 0
            })
        
        # Sort by total submitted
        team_metrics['member_data'].sort(key=lambda x: x['total_submitted'], reverse=True)
        
        return team_metrics
