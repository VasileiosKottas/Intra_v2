"""
Script to backup the database
"""

import sys
import os
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Backup the database"""
    # Database file path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'sales_dashboard.db')
    
    if not os.path.exists(db_path):
        print(" Database file not found!")
        return
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"sales_dashboard_backup_{timestamp}.db"
    backup_path = os.path.join(os.path.dirname(__file__), '..', 'backups', backup_filename)
    
    # Create backups directory if it doesn't exist
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    # Copy database file
    try:
        shutil.copy2(db_path, backup_path)
        print(f" Database backed up successfully!")
        print(f" Backup saved to: {backup_path}")
    except Exception as e:
        print(f" Backup failed: {e}")

if __name__ == '__main__':
    main()