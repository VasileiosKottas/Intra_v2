"""
Script to manually trigger data sync
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.services.sync import DataSyncService

def main():
    """Manually trigger data sync"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print(" Starting manual data sync...")
        
        # Sync both companies
        companies = ['windsor', 'cnc']
        
        for company in companies:
            print(f"\n Syncing data for {company.upper()}...")
            sync_service = DataSyncService(company)
            submissions_added, paid_cases_added, success, error = sync_service.perform_sync()
            
            if success:
                print(f" {company.upper()} sync completed!")
                print(f"   📥 Submissions added: {submissions_added}")
                print(f"   💰 Paid cases added: {paid_cases_added}")
            else:
                print(f" {company.upper()} sync failed: {error}")
        
        print("\n Manual sync process completed!")

if __name__ == '__main__':
    main()