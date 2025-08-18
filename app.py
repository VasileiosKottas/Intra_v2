#!/usr/bin/env python3
"""
Sales Dashboard System - ENHANCED VERSION with Shared Advisors and Team Management
Main application with automatic sync and fixed name matching
Now supports shared advisors between Windsor and CnC companies
Added: Team editing, deletion, and company-specific dashboard viewing
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests
import json
import os
from functools import wraps
import calendar
import threading
import time
import schedule
from sqlalchemy import or_, and_
from flask_cors import CORS


sync_manager = None
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

db_path = os.path.join(basedir, "instance", "sales_dashboard.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + db_path
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
JOTFORM_API_KEY = os.getenv('JOTFORM_API_KEY', 'b78b083ca0a78392acf8de69666a3577')
origins = os.getenv('CORS_ORIGINS', '*')
CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in origins.split(',') if o.strip()]}})

db = SQLAlchemy(app)

# COMPANY-SPECIFIC CONFIGURATIONS
COMPANY_CONFIGS = {
    'windsor': {
        'name': 'Windsor',
        'logo': 'White_and_teal_on_blue_2.png',
        'valid_business_types': [
            'Residential Mortgage (Including BTL)',
            'Personal Insurance (Including GI)',
            'Product Transfer'
        ],
        'valid_paid_case_types': [
            'Residential',
            'General Insurance',
            'Term insurance',
            'Other Referral'
        ],
        'advisor_names': [
            'Daniel Jones', 'Drew Gibson', 'Elliot Cotterell',
            'Jamie Cope', 'Lottie Brown', 'Martyn Barberry', 'Michael Olivieri',
            'Oliver Cotterell', 'Rachel Ashworth', 'Steven Horn', 'Nick Snailum (Referral)',
            'Chris Bailey - Leaver', 'James Thomas - Leaver'
        ],
        'name_mappings': {
            'mike': 'Michael Olivieri',
            'michael': 'Michael Olivieri',
            'mike olivieri': 'Michael Olivieri',
            'michael olivieri': 'Michael Olivieri',
            'steve': 'Steven Horn',
            'steven': 'Steven Horn',
            'steve horn': 'Steven Horn',
            'steven horn': 'Steven Horn',
            'dan': 'Daniel Jones',
            'daniel': 'Daniel Jones',
            'dan jones': 'Daniel Jones',
            'daniel jones': 'Daniel Jones',
            'drew': 'Drew Gibson',
            'drew gibson': 'Drew Gibson',
            'jamie': 'Jamie Cope',
            'jamie cope': 'Jamie Cope',
            'oliver': 'Oliver Cotterell',
            'oliver cotterell': 'Oliver Cotterell',
            'elliot': 'Elliot Cotterell',
            'elliot cotterell': 'Elliot Cotterell',
            'rachel': 'Rachel Ashworth',
            'rachel ashworth': 'Rachel Ashworth',
            'lottie': 'Lottie Brown',
            'lottie brown': 'Lottie Brown',
            'martyn': 'Martyn Barberry',
            'martyn barberry': 'Martyn Barberry',
            'nick': 'Nick Snailum (Referral)',
            'nick snailum': 'Nick Snailum (Referral)',
            'chris': 'Chris Bailey - Leaver',
            'chris bailey': 'Chris Bailey - Leaver',
            'james': 'James Thomas - Leaver',
            'james thomas': 'James Thomas - Leaver',
        }
    },
    'cnc': {
        'name': 'C&C',
        'logo': 'CnC.png',
        'valid_business_types': [
            'Bridging or Development',
            'Commercial',
            '2nd Charge - Regulated',
            '2nd Charge - Unregulated',
            'Development',
            'Business Loan'
        ],
        'valid_paid_case_types': [
            'Bridging or Development',
            'Commercial',
            '2nd Charge - Regulated',
            '2nd Charge - Unregulated',
            'Development',
            'Business Loan'
        ],
        'advisor_names': [
            'Daniel Jones', 'Drew Gibson', 'Elliot Cotterell',
            'Jamie Cope', 'Lottie Brown', 'Martyn Barberry', 'Michael Olivieri',
            'Oliver Cotterell', 'Rachel Ashworth', 'Steven Horn', 'Nick Snailum (Referral)',
            'Chris Bailey - Leaver', 'James Thomas - Leaver'
        ],
        'name_mappings': {
            'mike': 'Michael Olivieri',
            'michael': 'Michael Olivieri',
            'mike olivieri': 'Michael Olivieri',
            'michael olivieri': 'Michael Olivieri',
            'steve': 'Steven Horn',
            'steven': 'Steven Horn',
            'steve horn': 'Steven Horn',
            'steven horn': 'Steven Horn',
            'dan': 'Daniel Jones',
            'daniel': 'Daniel Jones',
            'dan jones': 'Daniel Jones',
            'daniel jones': 'Daniel Jones',
            'drew': 'Drew Gibson',
            'drew gibson': 'Drew Gibson',
            'jamie': 'Jamie Cope',
            'jamie cope': 'Jamie Cope',
            'oliver': 'Oliver Cotterell',
            'oliver cotterell': 'Oliver Cotterell',
            'elliot': 'Elliot Cotterell',
            'elliot cotterell': 'Elliot Cotterell',
            'rachel': 'Rachel Ashworth',
            'rachel ashworth': 'Rachel Ashworth',
            'lottie': 'Lottie Brown',
            'lottie brown': 'Lottie Brown',
            'martyn': 'Martyn Barberry',
            'martyn barberry': 'Martyn Barberry',
            'nick': 'Nick Snailum (Referral)',
            'nick snailum': 'Nick Snailum (Referral)',
            'chris': 'Chris Bailey - Leaver',
            'chris bailey': 'Chris Bailey - Leaver',
            'james': 'James Thomas - Leaver',
            'james thomas': 'James Thomas - Leaver',
        }
    }
}

def get_current_company():
    """Get current company from session, default to windsor"""
    return session.get('company_mode', 'windsor')

def get_company_config():
    """Get configuration for current company"""
    return COMPANY_CONFIGS[get_current_company()]

def get_valid_business_types():
    """Get valid business types for current company"""
    return get_company_config()['valid_business_types']

def get_valid_paid_case_types():
    """Get valid paid case types for current company"""
    return get_company_config()['valid_paid_case_types']

def get_available_advisors():
    """Get available advisor names for current company"""
    return get_company_config()['advisor_names']

def get_name_mappings():
    """Get name mappings for current company"""
    return get_company_config()['name_mappings']

def _parse_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None
    
def resolve_period_dates():
    """Resolve period dates with support for custom range"""
    period = request.args.get('period', 'month')
    today = datetime.now().date()
    
    if period == 'custom':
        start = _parse_date(request.args.get('start'))
        end = _parse_date(request.args.get('end'))
        if not start or not end or start > end:
            # fallback: last 30 days
            return today.replace(day=1), today
        return start, end
    elif period == 'quarter': 
        return today - timedelta(days=90), today
    elif period == 'year':    
        return today - timedelta(days=365), today
    else:  # month to date
        return today.replace(day=1), today

def backfill_advisor_links(advisor):
    """Link existing records by exact advisor name to this advisor's ID."""
    # Submissions
    subs = Submission.query.filter(
        Submission.advisor_name == advisor.full_name,
        Submission.advisor_id.is_(None)
    ).all()
    for s in subs:
        s.advisor_id = advisor.id

    # Paid cases
    paids = PaidCase.query.filter(
        PaidCase.advisor_name == advisor.full_name,
        PaidCase.advisor_id.is_(None)
    ).all()
    for p in paids:
        p.advisor_id = advisor.id

    db.session.commit()

# Enhanced Database Models with many-to-many relationship for advisors and teams
class AdvisorTeam(db.Model):
    __tablename__ = 'advisor_teams'
    
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    yearly_goal = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('advisor_id', 'team_id', name='unique_advisor_team'),)

class Advisor(db.Model):
    __tablename__ = 'advisors'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_master = db.Column(db.Boolean, default=False)
    # Remove company field - advisors are now shared
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with teams
    team_memberships = db.relationship('AdvisorTeam', backref='advisor', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='advisor')
    paid_cases = db.relationship('PaidCase', backref='advisor')
    
    def get_team_for_company(self, company):
        """Get the team for a specific company"""
        for membership in self.team_memberships:
            if membership.team.company == company:
                return membership.team
        return None
    
    def get_yearly_goal_for_company(self, company):
        """Get yearly goal for a specific company"""
        for membership in self.team_memberships:
            if membership.team.company == company:
                return membership.yearly_goal
        return 0.0

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    monthly_goal = db.Column(db.Float, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), default='windsor')  # Keep company for teams
    is_hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('Advisor', foreign_keys=[created_by], post_update=True)
    # Many-to-many relationship with advisors
    advisor_memberships = db.relationship('AdvisorTeam', backref='team', cascade='all, delete-orphan')
    
    @property
    def members(self):
        """Get all advisors in this team"""
        return [membership.advisor for membership in self.advisor_memberships]

class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    advisor_name = db.Column(db.String(100), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    business_type = db.Column(db.String(100), nullable=False)
    submission_date = db.Column(db.Date, nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    expected_proc = db.Column(db.Float, default=0.0)
    expected_fee = db.Column(db.Float, default=0.0)
    referral_to = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(50), default='windsor')
    jotform_id = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaidCase(db.Model):
    __tablename__ = 'paid_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    advisor_name = db.Column(db.String(100), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=True)
    case_type = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    value = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.Date, nullable=False)
    company = db.Column(db.String(50), default='windsor')
    jotform_id = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    submissions_synced = db.Column(db.Integer, default=0)
    paid_cases_synced = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='success')
    error_message = db.Column(db.Text, nullable=True)
    company = db.Column(db.String(50), default='windsor')

# Enhanced Data Management Class with company-specific filtering
class DataManager:
    """Handles JotForm data extraction and cleaning"""
    
    SUBMISSION_FORM_ID = "250232251408041"
    PAID_FORM_ID = "251406545360048"
    BASE_URL = "https://eu-api.jotform.com"
    
    SUBMISSION_FIELD_MAP = {
        'advisor_name': '39',
        'business_type': '3',
        'submission_date': '6',
        'customer_name': '7',
        'expected_proc': '12',
        'expected_fee': '13'
    }
    
    PAID_FIELD_MAP = {
        'advisor_name': '5',
        'case_type': '8',
        'value': '12',
        'customer_name': '4',
        'date_paid': '13'
    }
    
    def __init__(self, api_key, company='windsor'):
        self.api_key = api_key
        self.company = company
        self.company_config = COMPANY_CONFIGS[company]
        self.headers = {
            "APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the JotForm API"""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            return None
    
    def clean_advisor_name(self, name):
        """Clean and standardize advisor names with company-specific mapping"""
        if not name or name == "No Answer":
            return None
        
        name_clean = name.lower().strip()
        name_mappings = self.company_config['name_mappings']
        
        # Try exact mapping first
        if name_clean in name_mappings:
            return name_mappings[name_clean]
        
        # Try partial matching for complex names
        for key, standard_name in name_mappings.items():
            if key in name_clean or name_clean in key:
                return standard_name
        
        # If no mapping found, return cleaned version
        return name.title().strip()
    
    def parse_date(self, date_string):
        """Parse date from JotForm format to date object"""
        try:
            if isinstance(date_string, dict):
                if 'day' in date_string and 'month' in date_string and 'year' in date_string:
                    day = date_string.get('day', '01')
                    month = date_string.get('month', '01')
                    year = date_string.get('year', '2025')
                    date_str = f"{day}/{month}/{year}"
                    return datetime.strptime(date_str, '%d/%m/%Y').date()
                elif 'datetime' in date_string:
                    datetime_str = date_string.get('datetime', '')
                    return datetime.strptime(datetime_str.split()[0], '%Y-%m-%d').date()
            
            if isinstance(date_string, str):
                if ' ' in date_string:
                    date_part = date_string.split()[0]
                else:
                    date_part = date_string
                
                for date_format in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(date_part, date_format).date()
                    except ValueError:
                        continue
            
            return None
        except Exception as e:
            print(f"Error parsing date '{date_string}': {e}")
            return None
    
    def get_form_submissions_with_mapping(self, form_id, field_map, limit=1000):
        """Get form submissions using exact field mappings"""
        print(f"Fetching submissions for form {form_id} (Company: {self.company})...")
        
        endpoint = f"/form/{form_id}/submissions"
        params = {"limit": limit}
        response = self._make_request(endpoint, params)
        
        if not response:
            return []
        
        submissions = response.get("content", [])
        print(f"Retrieved {len(submissions)} raw submissions")
        
        parsed_submissions = []
        
        for submission in submissions:
            parsed_data = {
                "submission_id": submission.get("id"),
                "created_at": submission.get("created_at"),
                "status": submission.get("status"),
                "mapped_data": {}
            }
            
            answers = submission.get("answers", {})
            
            for data_key, question_id in field_map.items():
                if question_id in answers:
                    answer_data = answers[question_id]
                    if isinstance(answer_data, dict):
                        answer_value = answer_data.get("answer", "")
                    else:
                        answer_value = str(answer_data)
                    parsed_data["mapped_data"][data_key] = answer_value
                else:
                    parsed_data["mapped_data"][data_key] = ""
            
            parsed_submissions.append(parsed_data)
        
        return parsed_submissions
    
    def process_submissions(self):
        """Process submissions with company-specific filtering"""
        print(f"Processing submissions from JotForm for {self.company}...")
        
        submissions_data = self.get_form_submissions_with_mapping(
            self.SUBMISSION_FORM_ID, 
            self.SUBMISSION_FIELD_MAP
        )
        
        if not submissions_data:
            print("No submissions data retrieved")
            return []
        
        processed_submissions = []
        valid_business_types = self.company_config['valid_business_types']
        
        for submission in submissions_data:
            try:
                data = submission.get("mapped_data", {})
                
                advisor_name = self.clean_advisor_name(data.get("advisor_name", ""))
                business_type = str(data.get("business_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
                try:
                    proc_raw = data.get("expected_proc", "")
                    expected_proc = float(str(proc_raw).replace('£', '').replace(',', '') or 0)
                except (ValueError, TypeError):
                    expected_proc = 0
                    
                try:
                    fee_raw = data.get("expected_fee", "")
                    expected_fee = float(str(fee_raw).replace('£', '').replace(',', '') or 0)
                except (ValueError, TypeError):
                    expected_fee = 0
                
                submission_date = self.parse_date(data.get("submission_date", ""))
                if not submission_date:
                    submission_date = self.parse_date(submission.get("created_at", ""))
                
                referral_to = None
                if business_type and ('referral to' in business_type.lower() or business_type.lower().startswith('referral')):
                    if 'to' in business_type.lower():
                        referral_to = business_type.lower().split('to')[-1].strip().title()
                    else:
                        referral_to = business_type.replace('Referral', '').strip()
                    business_type = 'Referral'
                
                # Company-specific filtering: Only process valid business types OR referrals
                if advisor_name and (business_type in valid_business_types or business_type == 'Referral'):
                    processed_submissions.append({
                        'advisor_name': advisor_name,
                        'business_type': business_type,
                        'submission_date': submission_date or datetime.now().date(),
                        'customer_name': customer_name,
                        'expected_proc': expected_proc,
                        'expected_fee': expected_fee,
                        'referral_to': referral_to,
                        'company': self.company,
                        'jotform_id': submission.get("submission_id")
                    })
                    
            except Exception as e:
                print(f"Error processing submission: {e}")
                continue
        
        print(f"Successfully processed {len(processed_submissions)} valid submissions for {self.company}")
        return processed_submissions
    
    def process_paid_cases(self):
        """Process paid cases with company-specific filtering"""
        print(f"Processing paid cases from JotForm for {self.company}...")
        
        paid_data = self.get_form_submissions_with_mapping(
            self.PAID_FORM_ID, 
            self.PAID_FIELD_MAP
        )
        
        if not paid_data:
            print("No paid cases data retrieved")
            return []
        
        processed_cases = []
        valid_paid_case_types = self.company_config['valid_paid_case_types']
    
        for case in paid_data:
            try:
                data = case.get("mapped_data", {})
                
                advisor_name = self.clean_advisor_name(data.get("advisor_name", ""))
                case_type = str(data.get("case_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
                try:
                    value_raw = data.get("value", "")
                    if value_raw and value_raw != "No Answer":
                        value = float(str(value_raw).replace('£', '').replace(',', '') or 0)
                    else:
                        value = 0
                except (ValueError, TypeError):
                    value = 0
                
                date_paid = self.parse_date(data.get("date_paid", ""))
                if not date_paid:
                    date_paid = self.parse_date(case.get("created_at", ""))
                
                # Company-specific filtering
                if (advisor_name and 
                    case_type in valid_paid_case_types and 
                    value > 0):
                    processed_cases.append({
                        'advisor_name': advisor_name,
                        'case_type': case_type,
                        'value': value,
                        'customer_name': customer_name,
                        'date_paid': date_paid or datetime.now().date(),
                        'company': self.company,
                        'jotform_id': case.get("submission_id")
                    })
            except Exception as e:
                print(f"Error processing paid case: {e}")
                continue
        
        print(f"Successfully processed {len(processed_cases)} valid paid cases for {self.company}")
        return processed_cases

# Automatic Sync System with company support
class AutoSyncManager:
    """Manages automatic synchronization with JotForm for both companies"""
    
    def __init__(self):
        self.sync_running = False
    
    def sync_data_automatic(self, company='windsor'):
        """Automatic sync function for specific company"""
        if self.sync_running:
            print("Sync already running, skipping...")
            return
        
        self.sync_running = True
        print(f"🔄 Starting automatic sync for {company} at {datetime.now()}")
        
        try:
            with app.app_context():
                data_manager = DataManager(JOTFORM_API_KEY, company)
                
                # Sync submissions
                submissions = data_manager.process_submissions()
                submissions_added = 0
                
                for submission_data in submissions:
                    try:
                        existing = Submission.query.filter_by(jotform_id=submission_data['jotform_id']).first()
                        if not existing:
                            advisor = Advisor.query.filter_by(
                                full_name=submission_data['advisor_name']
                            ).first()
                            
                            submission = Submission(
                                advisor_name=submission_data['advisor_name'],
                                advisor_id=advisor.id if advisor else None,
                                business_type=submission_data['business_type'],
                                submission_date=submission_data['submission_date'],
                                customer_name=submission_data['customer_name'],
                                expected_proc=submission_data['expected_proc'],
                                expected_fee=submission_data['expected_fee'],
                                referral_to=submission_data['referral_to'],
                                company=company,
                                jotform_id=submission_data['jotform_id']
                            )
                            db.session.add(submission)
                            submissions_added += 1
                    except Exception as e:
                        print(f"Error adding submission: {e}")
                        continue
                
                # Sync paid cases
                paid_cases = data_manager.process_paid_cases()
                paid_cases_added = 0
                
                for case_data in paid_cases:
                    try:
                        existing = PaidCase.query.filter_by(jotform_id=case_data['jotform_id']).first()
                        if not existing:
                            advisor = Advisor.query.filter_by(
                                full_name=case_data['advisor_name']
                            ).first()
                            
                            paid_case = PaidCase(
                                advisor_name=case_data['advisor_name'],
                                advisor_id=advisor.id if advisor else None,
                                customer_name=case_data['customer_name'],
                                case_type=case_data['case_type'],
                                value=case_data['value'],
                                date_paid=case_data['date_paid'],
                                company=company,
                                jotform_id=case_data['jotform_id']
                            )
                            db.session.add(paid_case)
                            paid_cases_added += 1
                    except Exception as e:
                        print(f"Error adding paid case: {e}")
                        continue
                
                # Log the sync
                sync_log = SyncLog(
                    submissions_synced=submissions_added,
                    paid_cases_synced=paid_cases_added,
                    status='success',
                    company=company
                )
                db.session.add(sync_log)
                db.session.commit()
                
                print(f"✅ Auto sync completed for {company}! Added {submissions_added} submissions and {paid_cases_added} paid cases")
                
        except Exception as e:
            with app.app_context():
                sync_log = SyncLog(
                    status='error',
                    error_message=str(e),
                    company=company
                )
                db.session.add(sync_log)
                db.session.commit()
            print(f"❌ Auto sync failed for {company}: {e}")
        finally:
            self.sync_running = False
    
    def sync_all_companies(self):
        """Sync data for all companies"""
        for company in COMPANY_CONFIGS.keys():
            self.sync_data_automatic(company)
    
    def setup_scheduler(self):
        """Setup the sync schedule"""
        # Schedule sync at 9 AM and 5 PM daily for all companies
        schedule.every().day.at("09:00").do(self.sync_all_companies)
        schedule.every().day.at("17:00").do(self.sync_all_companies)
        
        # Schedule sync every 30 minutes between 9 AM and 5 PM for all companies
        for hour in range(9, 17):  # 9 AM to 4:30 PM
            for minute in [30]:  # 30 minutes past each hour
                schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.sync_all_companies)
        
        print("📅 Sync scheduler configured for all companies:")
        print("  - Daily at 9:00 AM and 5:00 PM")
        print("  - Every 30 minutes between 9:00 AM and 5:00 PM")
    
    def run_scheduler(self):
        """Run the scheduler in background"""
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

@app.after_request
def add_no_cache_headers(resp):
    if request.path.startswith('/api/'):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
    return resp

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = db.session.get(Advisor, session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = db.session.get(Advisor, session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        if not user.is_master:
            return jsonify({'error': 'Master access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get team data excluding hidden teams for regular users
def get_visible_team_members(user, current_company):
    """Get team members excluding those in hidden teams for regular users"""
    user_team = user.get_team_for_company(current_company)
    
    if user.is_master:
        # Masters can see all team members
        return user_team.members if user_team else []
    
    if not user_team or user_team.is_hidden:
        # If user is in a hidden team or no team, they only see themselves
        return [user]
    
    # Regular team members see all non-hidden team members
    return [member for member in user_team.members if not member.get_team_for_company(current_company) or not member.get_team_for_company(current_company).is_hidden]

# Company switching endpoint
@app.route('/api/set-company', methods=['POST'])
@login_required
def set_company():
    """Switch between company modes"""
    data = request.get_json()
    company = data.get('company', 'windsor')
    
    if company not in COMPANY_CONFIGS:
        return jsonify({'error': 'Invalid company'}), 400
    
    session['company_mode'] = company
    return jsonify({'success': True, 'company': company})

# Routes
@app.route('/')
@login_required
def dashboard():
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if user.is_master:
        return redirect(url_for('master_dashboard'))
    
    company_config = get_company_config()
    return render_template('dashboard.html', user=user, company_config=company_config)

@app.route('/master')
@master_required
def master_dashboard():
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    current_company = get_current_company()
    teams = Team.query.filter_by(company=current_company).all()
    advisors = Advisor.query.filter_by(is_master=False).all()  # Show all advisors
    all_advisor_names = get_available_advisors()
    recent_syncs = SyncLog.query.filter_by(company=current_company).order_by(SyncLog.sync_time.desc()).limit(10).all()
    
    company_config = get_company_config()
    return render_template('master.html', 
                         user=user, 
                         teams=teams, 
                         advisors=advisors, 
                         all_advisor_names=all_advisor_names,
                         recent_syncs=recent_syncs,
                         company_config=company_config)

# Master view of advisor dashboard - respects company selection
@app.route('/master/advisor/<int:advisor_id>')
@master_required
def view_advisor_dashboard(advisor_id):
    """Master can view any advisor's dashboard for the selected company"""
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return "Advisor not found", 404
    
    current_company = get_current_company()
    company_config = get_company_config()
    return render_template('advisor_view.html', 
                         advisor=advisor, 
                         company_config=company_config,
                         is_master_view=True,
                         current_company=current_company)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = Advisor.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['company_mode'] = 'windsor'  # Default to windsor
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if Advisor.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists', available_advisors=get_available_advisors())
        
        if Advisor.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists', available_advisors=get_available_advisors())
        
        user = Advisor(
            full_name=full_name,
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_master=False
        )
        
        db.session.add(user)
        db.session.commit()
        backfill_advisor_links(user)

        session['user_id'] = user.id
        session['company_mode'] = 'windsor'
        return redirect(url_for('dashboard'))
    
    available_advisors = get_available_advisors()
    return render_template('register.html', available_advisors=available_advisors)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# API Routes
@app.route('/api/dashboard-data')
@login_required
def get_dashboard_data():
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    start_date, end_date = resolve_period_dates()
    
    # Get submissions for this user (company-filtered)
    all_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= start_date,
            Submission.submission_date <= end_date,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == user.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == user.full_name)
            )
        )
    ).all()
    
    # Filter for valid business types
    submissions = [s for s in all_submissions if s.business_type in valid_business_types]
    referrals = [s for s in all_submissions if s.business_type.startswith('Referral')]
    
    # Get paid cases (company-filtered)
    paid_cases = PaidCase.query.filter(
        and_(
            PaidCase.date_paid >= start_date,
            PaidCase.date_paid <= end_date,
            PaidCase.company == current_company,
            PaidCase.case_type.in_(valid_paid_case_types),
            or_(
                PaidCase.advisor_id == user.id,
                and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == user.full_name)
            )
        )
    ).all()
    
    # Calculate totals
    total_submitted = sum(s.expected_proc or 0 for s in submissions)
    total_fee = sum(s.expected_fee or 0 for s in submissions)
    total_paid = sum(p.value for p in paid_cases)
    
    # Applications count
    applications = {}
    for submission in submissions:
        if submission.business_type not in applications:
            applications[submission.business_type] = 0
        applications[submission.business_type] += 1
    
    # Count referrals
    referrals_made = len(referrals)
    referrals_received = 0
    if user.full_name.lower() in ['steven horn', 'daniel jones']:
        referrals_received = len([r for r in all_submissions 
                                if r.business_type and ('steve' in r.business_type.lower() or 'daniel' in r.business_type.lower())])
    
    return jsonify({
        'total_submitted': total_submitted,
        'total_fee': total_fee,
        'combined_total': total_submitted + total_fee,
        'total_paid': total_paid,
        'payment_percentage': (total_paid / (total_submitted + total_fee) * 100) if (total_submitted + total_fee) > 0 else 0,
        'applications': applications,
        'referrals_made': referrals_made,
        'referrals_received': referrals_received,
        'company': current_company
    })

# API endpoint for master to get advisor dashboard data
@app.route('/api/advisor-dashboard-data/<int:advisor_id>')
@master_required
def get_advisor_dashboard_data(advisor_id):
    """Get dashboard data for a specific advisor (master only)"""
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify({'error': 'Advisor not found'}), 404
    
    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    start_date, end_date = resolve_period_dates()
    
    # Get submissions for this advisor
    all_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= start_date,
            Submission.submission_date <= end_date,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == advisor.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == advisor.full_name)
            )
        )
    ).all()
    
    submissions = [s for s in all_submissions if s.business_type in valid_business_types]
    referrals = [s for s in all_submissions if s.business_type.startswith('Referral')]
    
    # Get paid cases
    paid_cases = PaidCase.query.filter(
        and_(
            PaidCase.date_paid >= start_date,
            PaidCase.date_paid <= end_date,
            PaidCase.company == current_company,
            PaidCase.case_type.in_(valid_paid_case_types),
            or_(
                PaidCase.advisor_id == advisor.id,
                and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == advisor.full_name)
            )
        )
    ).all()
    
    # Calculate totals
    total_submitted = sum(s.expected_proc or 0 for s in submissions)
    total_fee = sum(s.expected_fee or 0 for s in submissions)
    total_paid = sum(p.value for p in paid_cases)
    
    # Applications count
    applications = {}
    for submission in submissions:
        if submission.business_type not in applications:
            applications[submission.business_type] = 0
        applications[submission.business_type] += 1
    
    # Count referrals
    referrals_made = len(referrals)
    referrals_received = 0
    if advisor.full_name.lower() in ['steven horn', 'daniel jones']:
        referrals_received = len([r for r in all_submissions 
                                if r.business_type and ('steve' in r.business_type.lower() or 'daniel' in r.business_type.lower())])
    
    return jsonify({
        'total_submitted': total_submitted,
        'total_fee': total_fee,
        'combined_total': total_submitted + total_fee,
        'total_paid': total_paid,
        'payment_percentage': (total_paid / (total_submitted + total_fee) * 100) if (total_submitted + total_fee) > 0 else 0,
        'applications': applications,
        'referrals_made': referrals_made,
        'referrals_received': referrals_received,
        'company': current_company,
        'advisor_name': advisor.full_name
    })

@app.route('/api/user-cases')
@login_required
def get_user_cases():
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        return jsonify([])

    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    case_type_filter = request.args.get('case_type', 'all')
    data_type = request.args.get('data_type', 'submitted')
    start_date, end_date = resolve_period_dates()

    if data_type == 'submitted':
        all_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == user.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == user.full_name)
                )
            )
        ).order_by(Submission.submission_date.desc()).all()
        
        if case_type_filter == 'all':
            cases = [s for s in all_submissions if s.business_type in valid_business_types]
        else:
            cases = [s for s in all_submissions if s.business_type == case_type_filter]

        return jsonify([
            {
                'customer_name': s.customer_name,
                'case_type': s.business_type,
                'fee_submitted': float((s.expected_fee or 0) + (s.expected_proc or 0)),
                'payment_status': 'Pending',
                'date': s.submission_date.strftime('%d %b'),
                'data_type': 'Submitted'
            } for s in cases
        ])
    else:
        query = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == current_company,
                PaidCase.case_type.in_(valid_paid_case_types),
                or_(
                    PaidCase.advisor_id == user.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == user.full_name)
                )
            )
        )
        if case_type_filter != 'all':
            query = query.filter(PaidCase.case_type == case_type_filter)

        cases = query.order_by(PaidCase.date_paid.desc()).all()

        return jsonify([
            {
                'customer_name': p.customer_name or 'Unknown Customer',
                'case_type': p.case_type,
                'fee_submitted': float(p.value or 0),
                'payment_status': 'Paid',
                'date': p.date_paid.strftime('%d %b'),
                'data_type': 'Paid'
            } for p in cases
        ])

# API endpoint for master to get advisor cases
@app.route('/api/advisor-cases/<int:advisor_id>')
@master_required
def get_advisor_cases(advisor_id):
    """Get cases for a specific advisor (master only)"""
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify([])

    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    case_type_filter = request.args.get('case_type', 'all')
    data_type = request.args.get('data_type', 'submitted')
    start_date, end_date = resolve_period_dates()

    if data_type == 'submitted':
        all_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == advisor.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == advisor.full_name)
                )
            )
        ).order_by(Submission.submission_date.desc()).all()
        
        if case_type_filter == 'all':
            cases = [s for s in all_submissions if s.business_type in valid_business_types]
        else:
            cases = [s for s in all_submissions if s.business_type == case_type_filter]

        return jsonify([
            {
                'customer_name': s.customer_name,
                'case_type': s.business_type,
                'fee_submitted': float((s.expected_fee or 0) + (s.expected_proc or 0)),
                'payment_status': 'Pending',
                'date': s.submission_date.strftime('%d %b'),
                'data_type': 'Submitted'
            } for s in cases
        ])
    else:
        query = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == current_company,
                PaidCase.case_type.in_(valid_paid_case_types),
                or_(
                    PaidCase.advisor_id == advisor.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == advisor.full_name)
                )
            )
        )
        if case_type_filter != 'all':
            query = query.filter(PaidCase.case_type == case_type_filter)

        cases = query.order_by(PaidCase.date_paid.desc()).all()

        return jsonify([
            {
                'customer_name': p.customer_name or 'Unknown Customer',
                'case_type': p.case_type,
                'fee_submitted': float(p.value or 0),
                'payment_status': 'Paid',
                'date': p.date_paid.strftime('%d %b'),
                'data_type': 'Paid'
            } for p in cases
        ])

@app.route('/api/team-data')
@login_required
def get_team_data():
    user = db.session.get(Advisor, session['user_id'])
    current_company = get_current_company()
    user_team = user.get_team_for_company(current_company)
    
    if not user_team:
        return jsonify({'no_team': True})

    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    start_date, end_date = resolve_period_dates()

    # Get visible team members (excludes hidden team members for regular users)
    visible_members = get_visible_team_members(user, current_company)
    
    team_members = []
    for member in visible_members:
        all_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == member.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == member.full_name)
                )
            )
        ).all()
        
        submissions = [s for s in all_submissions if s.business_type in valid_business_types]

        paid_cases = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == current_company,
                PaidCase.case_type.in_(valid_paid_case_types),
                or_(
                    PaidCase.advisor_id == member.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == member.full_name)
                )
            )
        ).all()
        
        total_submitted = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in submissions)
        total_paid = sum((p.value or 0) for p in paid_cases)
        avg_case_size = (total_paid / len(paid_cases)) if paid_cases else 0.0
        yearly_goal = member.get_yearly_goal_for_company(current_company)
        goal_progress = (total_submitted / yearly_goal * 100) if yearly_goal > 0 else 0.0

        team_members.append({
            'name': member.full_name,
            'total_submitted': total_submitted,
            'total_paid': total_paid,
            'avg_case_size': avg_case_size,
            'goal_progress': goal_progress
        })

    team_members.sort(key=lambda m: m['total_submitted'], reverse=True)

    # Team monthly goal (always current month)
    today = datetime.now().date()
    current_month_start = today.replace(day=1)
    
    all_team_submissions = []
    for member in visible_members:
        member_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= current_month_start,
                Submission.submission_date <= today,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == member.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == member.full_name)
                )
            )
        ).all()
        all_team_submissions.extend(member_submissions)
    
    team_monthly_submissions = [s for s in all_team_submissions if s.business_type in valid_business_types]
    team_monthly_total = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in team_monthly_submissions)
    
    # For hidden teams, don't show team goals to regular members
    if user_team.is_hidden and not user.is_master:
        team_goal = 0.0
        team_progress = 0.0
    else:
        team_goal = float(user_team.monthly_goal or 0.0)
        team_progress = (team_monthly_total / team_goal * 100) if team_goal > 0 else 0.0
    
    days_left = max(0, calendar.monthrange(today.year, today.month)[1] - today.day)
    total_paid_team = sum(m['total_paid'] for m in team_members)

    return jsonify({
        'team_name': user_team.name if not user_team.is_hidden or user.is_master else 'Personal Goals',
        'team_members': team_members,
        'team_progress': team_progress,
        'team_monthly_total': team_monthly_total,
        'team_monthly_goal': team_goal,
        'days_left': days_left,
        'total_paid': total_paid_team,
        'company': current_company,
        'is_hidden_team': user_team.is_hidden if user_team else False
    })

# API endpoint for master to get advisor team data
@app.route('/api/advisor-team-data/<int:advisor_id>')
@master_required
def get_advisor_team_data(advisor_id):
    """Get team data for a specific advisor (master only)"""
    advisor = db.session.get(Advisor, advisor_id)
    current_company = get_current_company()
    advisor_team = advisor.get_team_for_company(current_company) if advisor else None
    
    if not advisor or not advisor_team:
        return jsonify({'no_team': True})
    
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    start_date, end_date = resolve_period_dates()

    team_members = []
    for member in advisor_team.members:
        all_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == member.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == member.full_name)
                )
            )
        ).all()
        
        submissions = [s for s in all_submissions if s.business_type in valid_business_types]

        paid_cases = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == current_company,
                PaidCase.case_type.in_(valid_paid_case_types),
                or_(
                    PaidCase.advisor_id == member.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == member.full_name)
                )
            )
        ).all()
        
        total_submitted = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in submissions)
        total_paid = sum((p.value or 0) for p in paid_cases)
        avg_case_size = (total_paid / len(paid_cases)) if paid_cases else 0.0
        yearly_goal = member.get_yearly_goal_for_company(current_company)
        goal_progress = (total_submitted / yearly_goal * 100) if yearly_goal > 0 else 0.0

        team_members.append({
            'name': member.full_name,
            'total_submitted': total_submitted,
            'total_paid': total_paid,
            'avg_case_size': avg_case_size,
            'goal_progress': goal_progress
        })

    team_members.sort(key=lambda m: m['total_submitted'], reverse=True)

    # Team monthly goal (always current month)
    today = datetime.now().date()
    current_month_start = today.replace(day=1)
    
    all_team_submissions = []
    for member in advisor_team.members:
        member_submissions = Submission.query.filter(
            and_(
                Submission.submission_date >= current_month_start,
                Submission.submission_date <= today,
                Submission.company == current_company,
                or_(
                    Submission.advisor_id == member.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == member.full_name)
                )
            )
        ).all()
        all_team_submissions.extend(member_submissions)
    
    team_monthly_submissions = [s for s in all_team_submissions if s.business_type in valid_business_types]
    team_monthly_total = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in team_monthly_submissions)
    team_goal = float(advisor_team.monthly_goal or 0.0)
    team_progress = (team_monthly_total / team_goal * 100) if team_goal > 0 else 0.0
    days_left = max(0, calendar.monthrange(today.year, today.month)[1] - today.day)
    total_paid_team = sum(m['total_paid'] for m in team_members)

    return jsonify({
        'team_name': advisor_team.name,
        'team_members': team_members,
        'team_progress': team_progress,
        'team_monthly_total': team_monthly_total,
        'team_monthly_goal': team_goal,
        'days_left': days_left,
        'total_paid': total_paid_team,
        'company': current_company,
        'is_hidden_team': advisor_team.is_hidden
    })

@app.route('/api/performance-timeline')
@login_required
def get_performance_timeline():
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        return jsonify([])

    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    metric_type = request.args.get('type', 'submitted')
    start_date, end_date = resolve_period_dates()

    # Get submissions and paid cases
    all_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= start_date,
            Submission.submission_date <= end_date,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == user.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == user.full_name)
            )
        )
    ).all()
    
    submissions = [s for s in all_submissions if s.business_type in valid_business_types]

    paids = PaidCase.query.filter(
        and_(
            PaidCase.date_paid >= start_date,
            PaidCase.date_paid <= end_date,
            PaidCase.company == current_company,
            PaidCase.case_type.in_(valid_paid_case_types),
            or_(
                PaidCase.advisor_id == user.id,
                and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == user.full_name)
            )
        )
    ).all()

    # Index by date
    subs_by_date = {}
    for s in submissions:
        d = s.submission_date
        subs_by_date[d] = subs_by_date.get(d, 0.0) + float((s.expected_proc or 0) + (s.expected_fee or 0))

    paid_by_date = {}
    for p in paids:
        d = p.date_paid
        paid_by_date[d] = paid_by_date.get(d, 0.0) + float(p.value or 0)

    # Build cumulative series
    day = start_date
    running = 0.0
    series = []
    while day <= end_date:
        added = subs_by_date.get(day, 0.0) if metric_type == 'submitted' else paid_by_date.get(day, 0.0)
        running += added
        series.append({
            'date': day.strftime('%Y-%m-%d'),
            'value': round(running, 2)
        })
        day += timedelta(days=1)

    return jsonify(series)

# API endpoint for master to get advisor performance timeline
@app.route('/api/advisor-performance-timeline/<int:advisor_id>')
@master_required
def get_advisor_performance_timeline(advisor_id):
    """Get performance timeline for a specific advisor (master only)"""
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify([])

    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    valid_paid_case_types = get_valid_paid_case_types()
    
    metric_type = request.args.get('type', 'submitted')
    start_date, end_date = resolve_period_dates()

    # Get submissions and paid cases
    all_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= start_date,
            Submission.submission_date <= end_date,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == advisor.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == advisor.full_name)
            )
        )
    ).all()
    
    submissions = [s for s in all_submissions if s.business_type in valid_business_types]

    paids = PaidCase.query.filter(
        and_(
            PaidCase.date_paid >= start_date,
            PaidCase.date_paid <= end_date,
            PaidCase.company == current_company,
            PaidCase.case_type.in_(valid_paid_case_types),
            or_(
                PaidCase.advisor_id == advisor.id,
                and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == advisor.full_name)
            )
        )
    ).all()

    # Index by date
    subs_by_date = {}
    for s in submissions:
        d = s.submission_date
        subs_by_date[d] = subs_by_date.get(d, 0.0) + float((s.expected_proc or 0) + (s.expected_fee or 0))

    paid_by_date = {}
    for p in paids:
        d = p.date_paid
        paid_by_date[d] = paid_by_date.get(d, 0.0) + float(p.value or 0)

    # Build cumulative series
    day = start_date
    running = 0.0
    series = []
    while day <= end_date:
        added = subs_by_date.get(day, 0.0) if metric_type == 'submitted' else paid_by_date.get(day, 0.0)
        running += added
        series.append({
            'date': day.strftime('%Y-%m-%d'),
            'value': round(running, 2)
        })
        day += timedelta(days=1)

    return jsonify(series)

@app.route('/api/user-goal-data')
@login_required
def get_user_goal_data():
    """Get user's yearly goal progress"""
    user = db.session.get(Advisor, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    
    today = datetime.now().date()
    current_year_start = datetime(today.year, 1, 1).date()
    
    # Get yearly submissions
    all_yearly_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= current_year_start,
            Submission.submission_date <= today,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == user.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == user.full_name)
            )
        )
    ).all()
    
    valid_yearly_submissions = [s for s in all_yearly_submissions if s.business_type in valid_business_types]
    user_yearly_total = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in valid_yearly_submissions)
    user_yearly_goal = user.get_yearly_goal_for_company(current_company) or 50000.0
    user_yearly_progress = (user_yearly_total / user_yearly_goal * 100) if user_yearly_goal > 0 else 0.0
    user_yearly_remaining = max(0, user_yearly_goal - user_yearly_total)
    
    year_end = datetime(today.year, 12, 31).date()
    days_left_year = (year_end - today).days
    
    return jsonify({
        'user_yearly_total': user_yearly_total,
        'user_yearly_goal': user_yearly_goal,
        'user_yearly_progress': user_yearly_progress,
        'user_yearly_remaining': user_yearly_remaining,
        'days_left_year': days_left_year,
        'submissions_count': len(valid_yearly_submissions),
        'company': current_company
    })

# API endpoint for master to get advisor goal data
@app.route('/api/advisor-goal-data/<int:advisor_id>')
@master_required
def get_advisor_goal_data(advisor_id):
    """Get advisor's yearly goal progress (master only)"""
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify({'error': 'Advisor not found'}), 404
    
    current_company = get_current_company()
    valid_business_types = get_valid_business_types()
    
    today = datetime.now().date()
    current_year_start = datetime(today.year, 1, 1).date()
    
    # Get yearly submissions
    all_yearly_submissions = Submission.query.filter(
        and_(
            Submission.submission_date >= current_year_start,
            Submission.submission_date <= today,
            Submission.company == current_company,
            or_(
                Submission.advisor_id == advisor.id,
                and_(Submission.advisor_id.is_(None), Submission.advisor_name == advisor.full_name)
            )
        )
    ).all()
    
    valid_yearly_submissions = [s for s in all_yearly_submissions if s.business_type in valid_business_types]
    advisor_yearly_total = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in valid_yearly_submissions)
    advisor_yearly_goal = advisor.get_yearly_goal_for_company(current_company) or 50000.0
    advisor_yearly_progress = (advisor_yearly_total / advisor_yearly_goal * 100) if advisor_yearly_goal > 0 else 0.0
    advisor_yearly_remaining = max(0, advisor_yearly_goal - advisor_yearly_total)
    
    year_end = datetime(today.year, 12, 31).date()
    days_left_year = (year_end - today).days
    
    return jsonify({
        'user_yearly_total': advisor_yearly_total,
        'user_yearly_goal': advisor_yearly_goal,
        'user_yearly_progress': advisor_yearly_progress,
        'user_yearly_remaining': advisor_yearly_remaining,
        'days_left_year': days_left_year,
        'submissions_count': len(valid_yearly_submissions),
        'company': current_company,
        'advisor_name': advisor.full_name
    })

# Master API Routes
@app.route('/api/create-team', methods=['POST'])
@master_required
def create_team():
    data = request.get_json()
    current_company = get_current_company()
    
    team = Team(
        name=data['name'],
        monthly_goal=float(data.get('monthly_goal', 0)),
        created_by=session['user_id'],
        company=current_company,
        is_hidden=data.get('is_hidden', False)
    )
    db.session.add(team)
    db.session.commit()
    return jsonify({'success': True, 'team_id': team.id})

# NEW: Edit team endpoint
@app.route('/api/edit-team/<int:team_id>', methods=['PUT'])
@master_required
def edit_team(team_id):
    """Edit team details"""
    data = request.get_json()
    team = db.session.get(Team, team_id)
    
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    current_company = get_current_company()
    if team.company != current_company:
        return jsonify({'error': 'Team not in current company'}), 403
    
    # Update team details
    team.name = data.get('name', team.name)
    team.monthly_goal = float(data.get('monthly_goal', team.monthly_goal))
    team.is_hidden = data.get('is_hidden', team.is_hidden)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'Team {team.name} updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update team'}), 500

# NEW: Delete team endpoint
@app.route('/api/delete-team/<int:team_id>', methods=['DELETE'])
@master_required
def delete_team(team_id):
    """Delete a team and unassign all members"""
    team = db.session.get(Team, team_id)
    
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    
    current_company = get_current_company()
    if team.company != current_company:
        return jsonify({'error': 'Team not in current company'}), 403
    
    team_name = team.name
    
    try:
        # Delete all advisor-team relationships first
        AdvisorTeam.query.filter_by(team_id=team_id).delete()
        
        # Delete the team
        db.session.delete(team)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Team {team_name} deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete team'}), 500

@app.route('/api/assign-to-team', methods=['POST'])
@master_required
def assign_to_team():
    """Assign an advisor to a team"""
    data = request.get_json()
    advisor_id = data.get('advisor_id')
    team_id = data.get('team_id')
    yearly_goal = data.get('yearly_goal', 0)
    
    if not advisor_id or not team_id:
        return jsonify({'error': 'Advisor ID and Team ID required'}), 400
    
    advisor = db.session.get(Advisor, advisor_id)
    team = db.session.get(Team, team_id)
    
    if not advisor or not team:
        return jsonify({'error': 'Advisor or Team not found'}), 404
    
    current_company = get_current_company()
    if team.company != current_company:
        return jsonify({'error': 'Team not in current company'}), 403
    
    # Check if advisor is already in this team
    existing_membership = AdvisorTeam.query.filter_by(
        advisor_id=advisor_id,
        team_id=team_id
    ).first()
    
    if existing_membership:
        return jsonify({'error': 'Advisor already assigned to this team'}), 400
    
    # Check if advisor is already in another team for this company
    existing_company_team = None
    for membership in advisor.team_memberships:
        if membership.team.company == current_company:
            existing_company_team = membership.team
            break
    
    try:
        if existing_company_team:
            # Remove from existing team in this company
            AdvisorTeam.query.filter_by(
                advisor_id=advisor_id,
                team_id=existing_company_team.id
            ).delete()
        
        # Add to new team
        new_membership = AdvisorTeam(
            advisor_id=advisor_id,
            team_id=team_id,
            yearly_goal=float(yearly_goal)
        )
        db.session.add(new_membership)
        db.session.commit()
        
        message = f'Reassigned {advisor.full_name} from {existing_company_team.name} to {team.name}' if existing_company_team else f'Assigned {advisor.full_name} to {team.name}'
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to assign advisor'}), 500

@app.route('/api/unassign-from-team', methods=['POST'])
@master_required
def unassign_from_team():
    """Unassign an advisor from their team in current company"""
    data = request.get_json()
    advisor_id = data.get('advisor_id')
    
    if not advisor_id:
        return jsonify({'error': 'Advisor ID required'}), 400
    
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify({'error': 'Advisor not found'}), 404
    
    current_company = get_current_company()
    current_team = advisor.get_team_for_company(current_company)
    
    if not current_team:
        return jsonify({'error': 'Advisor not assigned to any team in this company'}), 400
    
    try:
        # Remove advisor from team in current company
        AdvisorTeam.query.filter_by(
            advisor_id=advisor_id,
            team_id=current_team.id
        ).delete()
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'{advisor.full_name} unassigned from {current_team.name}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to unassign advisor'}), 500

@app.route('/api/sync-now', methods=['POST'])
@master_required
def sync_now():
    """Manual sync trigger for master"""
    current_company = get_current_company()
    sync_manager.sync_data_automatic(current_company)
    return jsonify({'success': True, 'message': f'Sync completed for {current_company}'})

@app.route('/api/sync-status')
@master_required
def sync_status():
    """Get sync status and logs"""
    current_company = get_current_company()
    recent_syncs = SyncLog.query.filter_by(company=current_company).order_by(SyncLog.sync_time.desc()).limit(10).all()
    
    sync_data = []
    for sync in recent_syncs:
        sync_data.append({
            'time': sync.sync_time.strftime('%Y-%m-%d %H:%M:%S'),
            'submissions': sync.submissions_synced,
            'paid_cases': sync.paid_cases_synced,
            'status': sync.status,
            'error': sync.error_message,
            'company': sync.company
        })
    
    return jsonify(sync_data)
@app.route('/api/update-advisor-goal', methods=['PUT'])
@master_required
def update_advisor_goal():
    """Update an advisor's yearly goal for the current company"""
    data = request.get_json()
    advisor_id = data.get('advisor_id')
    yearly_goal = data.get('yearly_goal')
    company = data.get('company', get_current_company())
    
    if not advisor_id or yearly_goal is None:
        return jsonify({'error': 'Advisor ID and yearly goal are required'}), 400
    
    advisor = db.session.get(Advisor, advisor_id)
    if not advisor:
        return jsonify({'error': 'Advisor not found'}), 404
    
    # Find the advisor's team membership for the current company
    advisor_team_membership = None
    for membership in advisor.team_memberships:
        if membership.team.company == company:
            advisor_team_membership = membership
            break
    
    if not advisor_team_membership:
        return jsonify({'error': f'Advisor not assigned to any team in {company.upper()}'}), 400
    
    try:
        # Update the yearly goal
        advisor_team_membership.yearly_goal = float(yearly_goal)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Updated {advisor.full_name}\'s yearly goal to £{yearly_goal:,.0f} for {company.upper()}'
        })
    except ValueError:
        return jsonify({'error': 'Invalid yearly goal value'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update goal'}), 500
@app.route('/healthz')
def health():
    return {'ok': True}, 200

def create_master_user():
    """Create master user if it doesn't exist"""
    master = Advisor.query.filter_by(is_master=True).first()
    if not master:
        master = Advisor(
            full_name='Master Administrator',
            username='master',
            email='master@houseofwindsor.com',
            password_hash=generate_password_hash('master123'),
            is_master=True
        )
        db.session.add(master)
        db.session.commit()
        print("Master user created: username='master', password='master123'")

def create_sample_data():
    """Create sample data for testing"""
    if Advisor.query.filter_by(full_name='Jamie Cope').first():
        print("Sample data already exists")
        return
    
    print("Creating sample data...")
    
    advisors_data = [
        {'full_name': 'Jamie Cope', 'username': 'jamie', 'email': 'jamie@houseofwindsor.com'},
        {'full_name': 'Steven Horn', 'username': 'steven', 'email': 'steven@houseofwindsor.com'},
        {'full_name': 'Daniel Jones', 'username': 'daniel', 'email': 'daniel@houseofwindsor.com'},
        {'full_name': 'Drew Gibson', 'username': 'drew', 'email': 'drew@houseofwindsor.com'},
        {'full_name': 'Michael Olivieri', 'username': 'michael', 'email': 'michael@houseofwindsor.com'},
        {'full_name': 'Oliver Cotterell', 'username': 'oliver', 'email': 'oliver@houseofwindsor.com'},
        {'full_name': 'Elliot Cotterell', 'username': 'elliot', 'email': 'elliot@houseofwindsor.com'},
        {'full_name': 'Rachel Ashworth', 'username': 'rachel', 'email': 'rachel@houseofwindsor.com'},
        {'full_name': 'Lottie Brown', 'username': 'lottie', 'email': 'lottie@houseofwindsor.com'},
        {'full_name': 'Martyn Barberry', 'username': 'martyn', 'email': 'martyn@houseofwindsor.com'},
        {'full_name': 'Nick Snailum (Referral)', 'username': 'nick', 'email': 'nick@houseofwindsor.com'},
        {'full_name': 'Chris Bailey - Leaver', 'username': 'chris', 'email': 'chris@houseofwindsor.com'},
        {'full_name': 'James Thomas - Leaver', 'username': 'james', 'email': 'james@houseofwindsor.com'},
    ]
    
    created_advisors = []
    for advisor_data in advisors_data:
        advisor = Advisor(
            full_name=advisor_data['full_name'],
            username=advisor_data['username'],
            email=advisor_data['email'],
            password_hash=generate_password_hash('password123'),
            is_master=False
        )
        db.session.add(advisor)
        created_advisors.append(advisor)
    
    db.session.commit()
    
    # Create teams for both companies
    windsor_team = Team(
        name='Sales Team Alpha',
        monthly_goal=50000.0,
        created_by=1,
        company='windsor',
        is_hidden=False
    )
    db.session.add(windsor_team)
    
    windsor_hidden_team = Team(
        name='Performance Tracking',
        monthly_goal=30000.0,
        created_by=1,
        company='windsor',
        is_hidden=True
    )
    db.session.add(windsor_hidden_team)
    
    cnc_team = Team(
        name='CnC Development Team',
        monthly_goal=40000.0,
        created_by=1,
        company='cnc',
        is_hidden=False
    )
    db.session.add(cnc_team)
    
    db.session.commit()
    
    # Assign advisors to teams using the new relationship model
    # Windsor teams
    for i, advisor in enumerate(created_advisors[:4]):
        membership = AdvisorTeam(
            advisor_id=advisor.id,
            team_id=windsor_team.id,
            yearly_goal=50000.0
        )
        db.session.add(membership)
    
    for advisor in created_advisors[4:7]:
        membership = AdvisorTeam(
            advisor_id=advisor.id,
            team_id=windsor_hidden_team.id,
            yearly_goal=35000.0
        )
        db.session.add(membership)
    
    # CnC teams
    for advisor in created_advisors[7:10]:
        membership = AdvisorTeam(
            advisor_id=advisor.id,
            team_id=cnc_team.id,
            yearly_goal=45000.0
        )
        db.session.add(membership)
    
    db.session.commit()
    
    print("Sample data created successfully!")
    print("Sample advisor logins:")
    for advisor_data in advisors_data:
        print(f"  Username: {advisor_data['username']}, Password: password123")

if __name__ == '__main__':
    sync_manager = AutoSyncManager()
    with app.app_context():
        db.create_all()
        create_master_user()
        create_sample_data()
        sync_manager.sync_all_companies()

    sync_manager.setup_scheduler()
    threading.Thread(target=sync_manager.run_scheduler, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)