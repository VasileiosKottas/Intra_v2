"""
Base controller with common functionality
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
        """Get team members excluding those in hidden teams for regular users"""
        user_team = user.get_team_for_company(current_company)
        
        if user.is_master:
            # Masters can see all team members
            return user_team.members if user_team else []
        
        if not user_team or user_team.is_hidden:
            # If user is in a hidden team or no team, they only see themselves
            return [user]
        
        # Regular team members see all non-hidden team members
        return [member for member in user_team.members 
                if not member.get_team_for_company(current_company) or 
                not member.get_team_for_company(current_company).is_hidden]