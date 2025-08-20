"""
Main dashboard controller
"""

from flask import render_template, session, redirect, url_for
from app.controllers.base import BaseController
from app.config.session import SessionManager

class DashboardController(BaseController):
    """Handles main dashboard routes"""
    
    def register_routes(self):
        """Register dashboard routes"""
        self.app.add_url_rule('/', 'dashboard.index', self.login_required(self.index))
        self.app.add_url_rule('/healthz', 'dashboard.health', self.health)
    
    def index(self):
        """Main dashboard view"""

        user = self.get_current_user()
        
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        if user.is_master:
            return redirect(url_for('master.index'))
        
        company_config = SessionManager.get_company_config(session)
        return render_template('dashboard.html', user=user, company_config=company_config)
    
    def health(self):
        """Health check endpoint"""
        return {'ok': True}, 200