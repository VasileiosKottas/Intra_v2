#!/usr/bin/env python3
"""
Simple database migration to add call records table
Run this to add the call tracking functionality without initializing the full app
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    """Add call records table to database"""
    
    try:
        print("Creating minimal Flask app for migration...")
        
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        import os
        
        # Create minimal app
        app = Flask(__name__)
        
        # Database configuration
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, "instance", "sales_dashboard.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db = SQLAlchemy(app)
        
        with app.app_context():
            # Define the CallRecord model inline
            class CallRecord(db.Model):
                __tablename__ = 'call_records'
                
                id = db.Column(db.Integer, primary_key=True)
                sid = db.Column(db.String(100), nullable=False, index=True)
                advisor_email = db.Column(db.String(100), nullable=False, index=True)
                direction = db.Column(db.String(10), nullable=False)
                calling_number = db.Column(db.String(50))
                called_number = db.Column(db.String(50))
                call_start_time = db.Column(db.DateTime, nullable=False, index=True)
                call_answered_time = db.Column(db.DateTime)
                duration_seconds = db.Column(db.Integer, default=0)
                was_answered = db.Column(db.Boolean, default=False)
                was_voicemail = db.Column(db.Boolean, default=False)
                was_transferred = db.Column(db.Boolean, default=False)
                call_status = db.Column(db.String(50))
                company = db.Column(db.String(50), nullable=False, index=True)
                created_at = db.Column(db.DateTime, default=db.func.now())
                
                __table_args__ = (
                    db.UniqueConstraint('sid', 'company', name='unique_call_per_company'),
                    db.Index('idx_advisor_date_direction', 'advisor_email', 'call_start_time', 'direction'),
                )
            
            print("Adding call records table...")
            db.create_all()
            
            print("✓ Call records table created successfully!")
            print("\nTable structure:")
            print("- sid: Unique call identifier from ALTOS")
            print("- advisor_email: Email to link calls to advisors")
            print("- direction: I=Inbound, O=Outbound")
            print("- calling_number: Calling CLI")
            print("- called_number: Called CLI")
            print("- call_start_time: When call started ringing")
            print("- call_answered_time: When call was answered (if applicable)")
            print("- duration_seconds: Call duration")
            print("- was_answered: Boolean if call was picked up")
            print("- was_voicemail: Boolean if went to voicemail")
            print("- was_transferred: Boolean if call was transferred")
            print("- call_status: Reason if call failed")
            print("- company: Company identifier")
            print("\n✓ Migration completed successfully!")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_migration()