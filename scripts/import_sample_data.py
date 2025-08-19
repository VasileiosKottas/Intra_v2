"""
Script to import sample data
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.services.database import DatabaseService

def main():
    """Import sample data"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        db_service = DatabaseService()
        db_service.create_sample_data()
        print(" Sample data imported successfully!")

if __name__ == '__main__':
    main()
