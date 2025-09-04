"""
ALTOS API Sync Service - Integration with existing Sales Dashboard
This service fetches outbound call data from ALTOS API and integrates with your database
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.models import db
    from app.models.advisor import Advisor
    from app.config import config_manager
except ImportError:
    print("Warning: Could not import app modules. Running in standalone mode.")

class AltosCall:
    """Model for ALTOS call data"""
    def __init__(self, call_data):
        self.calling_number = call_data.get('cg', '')
        self.called_number = call_data.get('cd', '')
        self.direction = call_data.get('d', '')  # O=Outbound, I=Inbound
        self.start_time = self._parse_timestamp(call_data.get('rs', ''))
        self.duration = int(call_data.get('t', 0))  # seconds
        self.connected = bool(call_data.get('c', False))
        self.voicemail = bool(call_data.get('v', False))
        self.forwarded = bool(call_data.get('f', False))
        self.internal = bool(call_data.get('ic', False))
        self.conference = bool(call_data.get('co', False))
        self.raw_data = call_data
    
    def _parse_timestamp(self, timestamp_str):
        """Parse ALTOS timestamp format (YYYYMMDDHHMMSS)"""
        if not timestamp_str or len(timestamp_str) < 8:
            return None
        
        try:
            # Handle different timestamp formats
            if len(timestamp_str) >= 14:
                # Full format: YYYYMMDDHHMMSS
                return datetime.strptime(timestamp_str[:14], '%Y%m%d%H%M%S')
            elif len(timestamp_str) >= 8:
                # Date only: YYYYMMDD
                return datetime.strptime(timestamp_str[:8], '%Y%m%d')
        except ValueError:
            pass
        
        return None
    
    def is_outbound(self):
        """Check if this is an outbound call"""
        return self.direction == 'O'
    
    def is_answered(self):
        """Check if call was answered"""
        return self.connected and self.duration > 0
    
    def get_duration_minutes(self):
        """Get duration in minutes"""
        return round(self.duration / 60, 2) if self.duration else 0
    
    def to_dict(self):
        """Convert to dictionary for database storage"""
        return {
            'calling_number': self.calling_number,
            'called_number': self.called_number,
            'direction': self.direction,
            'call_start_time': self.start_time,
            'duration_seconds': self.duration,
            'duration_minutes': self.get_duration_minutes(),
            'connected': self.connected,
            'answered': self.is_answered(),
            'voicemail': self.voicemail,
            'forwarded': self.forwarded,
            'internal': self.internal,
            'conference': self.conference,
            'created_at': datetime.now(),
            'raw_data': json.dumps(self.raw_data)
        }

class AltosSyncService:
    """Service for syncing ALTOS call data"""
    
    def __init__(self):
        self.api_token = os.getenv('ALTOS_API_TOKEN', '58F22F24-3232-4490-98CE-C0B2A33A9048')
        self.base_url = "https://extprov.myphones.net/callhistory.aspx"
        self.data_dir = Path("altos_sync_logs")
        self.data_dir.mkdir(exist_ok=True)
    
    def is_api_available(self):
        """Check if API is available (midnight to 6 AM)"""
        current_hour = datetime.now().hour
        return 0 <= current_hour < 6
    
    def build_api_url(self, start_date, end_date, call_type='all'):
        """Build API URL for call history request"""
        # Format dates
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        sd = start_date.strftime('%Y%m%d')
        ed = end_date.strftime('%Y%m%d')
        
        params = {
            'ctok': self.api_token,
            'c': 'search',
            'ty': call_type,  # Use 'all' then filter for outbound
            'sd': sd,
            'ed': ed
        }
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def fetch_calls(self, start_date, end_date):
        """Fetch calls from ALTOS API"""
        if not self.is_api_available():
            raise Exception(f"API not available at {datetime.now().hour}:xx. Available 00:00-06:00 only.")
        
        url = self.build_api_url(start_date, end_date)
        
        print(f"📡 Fetching ALTOS calls from {start_date} to {end_date}")
        print(f"🔗 URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract calls
                calls_data = []
                if 'myphones' in data and 'callhistory' in data['myphones']:
                    calls_data = data['myphones']['callhistory']
                
                # Convert to AltosCall objects and filter for outbound
                calls = []
                for call_data in calls_data:
                    call = AltosCall(call_data)
                    if call.is_outbound():  # Only outbound calls
                        calls.append(call)
                
                print(f"📞 Found {len(calls)} outbound calls (from {len(calls_data)} total)")
                
                # Log raw response
                self._log_api_response(data, start_date, end_date)
                
                return calls
            
            else:
                raise Exception(f"API request failed: {response.status_code} - {response.text[:200]}")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request error: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    def _log_api_response(self, data, start_date, end_date):
        """Log API response for debugging"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.data_dir / f"altos_sync_{start_date}_{end_date}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'date_range': f"{start_date} to {end_date}",
                'response': data
            }, f, indent=2)
        
        print(f"💾 API response logged: {log_file}")
    
    def sync_yesterday_calls(self):
        """Sync calls from yesterday (main daily sync method)"""
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = start_date  # Same day
        
        return self.sync_calls_for_date_range(start_date, end_date)
    
    def sync_calls_for_date_range(self, start_date, end_date):
        """Sync calls for a specific date range"""
        try:
            print(f"🚀 Starting ALTOS sync for {start_date} to {end_date}")
            
            # Fetch calls from API
            calls = self.fetch_calls(start_date, end_date)
            
            if not calls:
                print("ℹ️  No outbound calls found for this period")
                return 0, True, None
            
            # Save to database (if database is available)
            saved_count = 0
            if 'db' in globals():
                saved_count = self._save_calls_to_database(calls)
            else:
                # Save to file if no database available
                saved_count = self._save_calls_to_file(calls, start_date, end_date)
            
            print(f"✅ ALTOS sync completed: {saved_count} calls processed")
            return saved_count, True, None
            
        except Exception as e:
            error_msg = f"ALTOS sync failed: {e}"
            print(f"❌ {error_msg}")
            return 0, False, error_msg
    
    def _save_calls_to_database(self, calls):
        """Save calls to database (integrate with your existing DB structure)"""
        # TODO: Create proper database table for ALTOS calls
        # For now, save to a simple structure
        
        saved_count = 0
        
        # This is a placeholder - you'll need to create a proper table
        # based on your database schema after analyzing the data structure
        
        for call in calls:
            try:
                # Here you would insert into your database
                # Example structure:
                call_data = call.to_dict()
                
                print(f"📱 Call: {call.calling_number} → {call.called_number} "
                      f"({call.get_duration_minutes()}min) at {call.start_time}")
                
                # TODO: Insert into database
                # db.session.add(AltosCallRecord(**call_data))
                
                saved_count += 1
                
            except Exception as e:
                print(f"⚠️  Failed to save call: {e}")
        
        # TODO: Commit database transaction
        # db.session.commit()
        
        return saved_count
    
    def _save_calls_to_file(self, calls, start_date, end_date):
        """Save calls to file when database is not available"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.data_dir / f"outbound_calls_{start_date}_{end_date}_{timestamp}.json"
        
        calls_data = [call.to_dict() for call in calls]
        
        with open(output_file, 'w') as f:
            json.dump({
                'sync_timestamp': timestamp,
                'date_range': f"{start_date} to {end_date}",
                'total_calls': len(calls_data),
                'calls': calls_data
            }, f, indent=2, default=str)  # default=str handles datetime objects
        
        print(f"💾 Calls saved to file: {output_file}")
        return len(calls_data)
    
    def generate_daily_report(self, start_date, end_date):
        """Generate a daily report of outbound calls"""
        try:
            calls = self.fetch_calls(start_date, end_date)
            
            if not calls:
                return "No outbound calls found for this period"
            
            # Calculate statistics
            total_calls = len(calls)
            answered_calls = sum(1 for call in calls if call.is_answered())
            total_duration = sum(call.duration for call in calls)
            avg_duration = total_duration / total_calls if total_calls > 0 else 0
            
            # Generate report
            report = f"""
📊 ALTOS Outbound Calls Report - {start_date} to {end_date}
{'='*60}
📞 Total Calls: {total_calls}
✅ Answered: {answered_calls} ({(answered_calls/total_calls)*100:.1f}%)
❌ Not Answered: {total_calls - answered_calls}
⏱️  Total Duration: {total_duration//60}m {total_duration%60}s
📈 Average Duration: {avg_duration//60}m {avg_duration%60}s

📋 Top Calling Numbers:
"""
            
            # Top calling numbers
            calling_numbers = {}
            for call in calls:
                calling_numbers[call.calling_number] = calling_numbers.get(call.calling_number, 0) + 1
            
            for number, count in sorted(calling_numbers.items(), key=lambda x: x[1], reverse=True)[:5]:
                report += f"   {number}: {count} calls\n"
            
            return report
            
        except Exception as e:
            return f"Failed to generate report: {e}"

# Integration with your existing sync system
class AltosAutoSyncManager:
    """Integration with your existing AutoSyncManager"""
    
    def __init__(self, app=None):
        self.app = app
        self.altos_service = AltosSyncService()
    
    def sync_altos_data_daily(self):
        """Method to be called by your existing scheduler at 3 AM"""
        print("🌙 Starting daily ALTOS sync at 3 AM...")
        
        if not self.altos_service.is_api_available():
            print("⚠️  ALTOS API not available at this time")
            return False
        
        # Sync yesterday's calls
        calls_count, success, error = self.altos_service.sync_yesterday_calls()
        
        if success:
            print(f"✅ ALTOS daily sync completed: {calls_count} calls processed")
            return True
        else:
            print(f"❌ ALTOS daily sync failed: {error}")
            return False
    
    def setup_altos_scheduler(self, scheduler):
        """Add ALTOS sync to your existing scheduler"""
        # Schedule ALTOS sync at 3 AM (within API window)
        scheduler.every().day.at("03:00").do(self.sync_altos_data_daily)
        print("📅 ALTOS sync scheduled for 3:00 AM daily")

def create_altos_database_table():
    """Create database table for ALTOS call data"""
    
    # SQL for creating the table - adjust based on your database structure
    sql_create_table = """
    CREATE TABLE IF NOT EXISTS altos_outbound_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        calling_number VARCHAR(20) NOT NULL,
        called_number VARCHAR(20) NOT NULL,
        direction CHAR(1) DEFAULT 'O',
        call_start_time DATETIME,
        duration_seconds INTEGER DEFAULT 0,
        duration_minutes DECIMAL(5,2) DEFAULT 0,
        connected BOOLEAN DEFAULT FALSE,
        answered BOOLEAN DEFAULT FALSE,
        voicemail BOOLEAN DEFAULT FALSE,
        forwarded BOOLEAN DEFAULT FALSE,
        internal BOOLEAN DEFAULT FALSE,
        conference BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        raw_data TEXT,
        
        -- Indexes for performance
        INDEX idx_call_start_time (call_start_time),
        INDEX idx_calling_number (calling_number),
        INDEX idx_called_number (called_number)
    );
    """
    
    print("📋 Database table SQL:")
    print(sql_create_table)
    
    # TODO: Execute this in your database initialization
    # This would go in your DatabaseService.create_tables() method


def manual_altos_sync():
    """Manual sync function for testing"""
    print("🔧 Manual ALTOS sync starting...")
    
    service = AltosSyncService()
    
    if not service.is_api_available():
        print(f"⚠️  API not available at {datetime.now().hour}:xx")
        print("API is only available between 00:00-06:00")
        return
    
    # Ask for date range
    print("Enter date range for sync:")
    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip() or start_date
    
    try:
        calls_count, success, error = service.sync_calls_for_date_range(start_date, end_date)
        
        if success:
            print(f"✅ Manual sync completed: {calls_count} calls processed")
            
            # Generate report
            report = service.generate_daily_report(start_date, end_date)
            print("\n" + report)
            
        else:
            print(f"❌ Manual sync failed: {error}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


# Integration instructions for your existing code
def integration_instructions():
    """Print integration instructions"""
    
    instructions = """
🔧 INTEGRATION INSTRUCTIONS FOR YOUR EXISTING SYSTEM:

1. ADD TO YOUR main.py:
   In your SalesDashboardApp.start_background_services() method, add:
   
   ```python
   # Add ALTOS sync manager
   from services.altos_sync import AltosAutoSyncManager
   self.altos_sync_manager = AltosAutoSyncManager(self.app)
   ```

2. ADD TO YOUR sync.py (AutoSyncManager):
   In your setup_hybrid_scheduler() method, add:
   
   ```python
   # Schedule ALTOS sync at 3 AM (within API window 00:00-06:00)
   schedule.every().day.at("03:00").do(self.sync_altos_daily)
   ```
   
   And add this method to your AutoSyncManager class:
   
   ```python
   def sync_altos_daily(self):
       \"\"\"Daily ALTOS call data sync\"\"\"
       from services.altos_sync import AltosSyncService
       
       altos_service = AltosSyncService()
       calls_count, success, error = altos_service.sync_yesterday_calls()
       
       if success:
           print(f"✅ ALTOS sync: {calls_count} calls processed")
       else:
           print(f"❌ ALTOS sync failed: {error}")
   ```

3. ADD TO YOUR database.py:
   In your DatabaseService.create_tables() method, add the ALTOS table creation.

4. ADD TO YOUR .env:
   Make sure you have:
   ```
   ALTOS_API_TOKEN=58F22F24-3232-4490-98CE-C0B2A33A9048
   ```

5. CREATE REPORTS INTEGRATION:
   You can add ALTOS call data to your existing reports by querying the 
   altos_outbound_calls table and joining with your advisors/teams data.

📊 REPORT IDEAS:
- Daily outbound call volume by advisor
- Call answer rates by time of day
- Average call duration trends
- Top called numbers (prospects/clients)
- Call activity correlation with sales results

🚀 NEXT STEPS:
1. Run the data capture script tonight to get the data structure
2. Create the database table based on the captured structure
3. Integrate the sync service into your existing system
4. Test the 3 AM daily sync
5. Add ALTOS data to your dashboard reports
"""
    
    print(instructions)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "manual":
            manual_altos_sync()
        elif command == "table":
            create_altos_database_table()
        elif command == "integration":
            integration_instructions()
        else:
            print("Usage: python altos_sync.py [manual|table|integration]")
    else:
        print("ALTOS Sync Service")
        print("Usage: python altos_sync.py [manual|table|integration]")
        print("\nCommands:")
        print("  manual      - Run manual sync (requires API window)")
        print("  table       - Show database table creation SQL")
        print("  integration - Show integration instructions")