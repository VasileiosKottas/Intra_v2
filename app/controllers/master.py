"""
Master dashboard controller
"""

from flask import render_template, session, redirect, url_for
from app.controllers.base import BaseController
from app.models.team import Team
from app.models.advisor import Advisor
from app.models.sync_log import SyncLog
from app.config.session import SessionManager
from app.config import config_manager
from app.models import db

class MasterController(BaseController):
    """Handles master dashboard routes"""
    
    def register_routes(self):
        """Register master dashboard routes"""
        self.app.add_url_rule('/master', 'master.index', self.master_required(self.index))
        self.app.add_url_rule('/master/advisor/<int:advisor_id>', 'master.view_advisor', 
                             self.master_required(self.view_advisor_dashboard))
    
    def index(self):
        """Master dashboard view"""
        user = self.get_current_user()
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        current_company = SessionManager.get_current_company(session)
        teams = Team.query.filter_by(company=current_company).all()
        advisors = Advisor.query.filter_by(is_master=False).all()
        all_advisor_names = config_manager.get_advisor_names(current_company)
        recent_syncs = SyncLog.query.filter_by(company=current_company).order_by(SyncLog.sync_time.desc()).limit(10).all()
        
        company_config = SessionManager.get_company_config(session)
        return render_template('master.html', 
                             user=user, 
                             teams=teams, 
                             advisors=advisors, 
                             all_advisor_names=all_advisor_names,
                             recent_syncs=recent_syncs,
                             company_config=company_config)
    
    def view_advisor_dashboard(self, advisor_id):
        """Master view of advisor dashboard"""
        advisor = db.session.get(Advisor, advisor_id)
        if not advisor:
            return "Advisor not found", 404
        
        current_company = SessionManager.get_current_company(session)
        company_config = SessionManager.get_company_config(session)
        return render_template('advisor_view.html', 
                             advisor=advisor, 
                             company_config=company_config,
                             is_master_view=True,
                             current_company=current_company)
