"""
Authentication controller
"""

from flask import render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.controllers.base import BaseController
from app.models.advisor import Advisor
from app.config.session import SessionManager
from app.config import config_manager

class AuthController(BaseController):
    """Handles authentication routes"""
    
    def register_routes(self):
        """Register authentication routes"""
        self.app.add_url_rule('/login', 'auth.login', self.login, methods=['GET', 'POST'])
        self.app.add_url_rule('/register', 'auth.register', self.register, methods=['GET', 'POST'])
        self.app.add_url_rule('/logout', 'auth.logout', self.logout)
    
    def login(self):
        """Handle login requests"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            user = Advisor.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['company_mode'] = 'windsor'  # Default to windsor
                return redirect(url_for('dashboard.index'))
            else:
                return render_template('login.html', error='Invalid credentials')
        
        return render_template('login.html')
    
    def register(self):
        """Handle registration requests"""
        current_company = SessionManager.get_current_company(session)
        available_advisors = config_manager.get_advisor_names(current_company)
        
        if request.method == 'POST':
            full_name = request.form['full_name']
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if Advisor.query.filter_by(username=username).first():
                return render_template('register.html', 
                                     error='Username already exists', 
                                     available_advisors=available_advisors)
            
            if Advisor.query.filter_by(email=email).first():
                return render_template('register.html', 
                                     error='Email already exists', 
                                     available_advisors=available_advisors)
            
            user = Advisor(
                full_name=full_name,
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_master=False
            )
            
            user.save()
            self.db_service.backfill_advisor_links(user)

            session['user_id'] = user.id
            session['company_mode'] = 'windsor'
            return redirect(url_for('dashboard.index'))
        
        return render_template('register.html', available_advisors=available_advisors)
    
    def logout(self):
        """Handle logout requests"""
        session.clear()
        return redirect(url_for('auth.login'))
