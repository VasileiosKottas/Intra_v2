"""
Base controller with common functionality - Updated for multiple teams
"""

from flask import session, request, jsonify, redirect, url_for
from functools import wraps
from app.models import db
from app.models.advisor import Advisor
from app.services.database import DatabaseService

class BaseController:
    """Base controller with common functionality"""
    
    def __init__(self, app):
        self.app = app
        self.db_service = DatabaseService()
        self.register_routes()
    
    def register_routes(self):
        """Register routes - to be implemented by subclasses"""
        pass
    
    def login_required(self, f):
        """Decorator for routes requiring authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            user = db.session.get(Advisor, session['user_id'])
            
            if not user:
                session.clear()
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    def master_required(self, f):
        """Decorator for routes requiring master access"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            user = db.session.get(Advisor, session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('auth.login'))
            
            if not user.is_master:
                return jsonify({'error': 'Master access required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    
    def get_current_user(self) -> Advisor:
        """Get current authenticated user"""
        user_id = session.get('user_id')
        if user_id:
            user = db.session.get(Advisor, user_id)
            return user
        return None
    
    def get_visible_team_members(self, user: Advisor, current_company: str) -> list:
        """Get team members that the user should see (handles multiple teams and visibility)"""
        if user.is_master:
            # Masters can see all members from the user's primary team (including hidden ones)
            primary_team = user.get_primary_team_for_company(current_company)
            return primary_team.members if primary_team else []
        
        user_team = user.get_team_for_company(current_company)
        if not user_team:
        # No team assignment
            return []
        if user_team.is_hidden:
            # If user is in a hidden team, they only see themselves
            return [user]
        
        # Get user's visible team (non-hidden)
        visible_team = user.get_visible_team_for_company(current_company)
        
        if visible_team:
            # User is in a visible team - show all members of that team
            # but exclude members who are ONLY in hidden teams
            visible_members = []
            for member in user_team.members:
                # Check if member is visible (not hidden from team)
                if member.is_visible_to_advisor(user):
                    visible_members.append(member)
            
            return visible_members
        else:
            # User is only in hidden teams or no teams - only show themselves
            return [user]
    
    def get_user_display_team(self, user: Advisor, current_company: str):
        """Get the team that should be displayed to the user"""
        if user.is_master:
            # Masters see the primary team
            return user.get_primary_team_for_company(current_company)
        
        # Regular users see their visible team, or their primary team if master is viewing
        visible_team = user.get_visible_team_for_company(current_company)
        if visible_team:
            return visible_team
        
        # If only in hidden teams, return None so they see "Personal Goals"
        return None