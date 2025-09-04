"""
ALTOS API Data Capture Script - Overnight Runner
This script runs between midnight and 6 AM to capture call data and analyze structure
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sqlite3
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class AltosDataCapturer:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://extprov.myphones.net/callhistory.aspx"
        self.data_dir = Path("altos_data_capture")
        self.data_dir.mkdir(exist_ok=True)
        
    def is_api_available_time(self):
        """Check if current time is within API availability (midnight to 6 AM)"""
        current_hour = datetime.now().hour
        return 0 <= current_hour < 6
    
    def wait_for_api_window(self):
        """Wait until API is available (midnight to 6 AM)"""
        while not self.is_api_available_time():
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 {current_time} - Waiting for API window (00:00-06:00)...")
            print("💤 Sleeping for 10 minutes...")
            time.sleep(600)  # Sleep for 10 minutes
            
        print("🎯 API window is now open! Starting data capture...")
    
    def build_api_url(self, start_date, end_date, call_type='all'):
        """Build API URL with parameters"""
        # Format dates (YYYYMMDD)
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        sd = start_date.strftime('%Y%m%d')
        ed = end_date.strftime('%Y%m%d')
        
        params = {
            'ctok': self.api_token,
            'c': 'search',
            'ty': call_type,  # 'all', 'made', 'received', etc.
            'sd': sd,
            'ed': ed
        }
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def make_api_request(self, url):
        """Make API request with error handling"""
        print(f"📡 Making API request: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📄 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ Successfully parsed JSON response")
                    return data, None
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON: {e}"
                    print(f"❌ {error_msg}")
                    return None, error_msg
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"❌ {error_msg}")
                return None, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            print(f"❌ {error_msg}")
            return None, error_msg
    
    def analyze_data_structure(self, data, call_type):
        """Analyze and document the data structure"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw data
        raw_file = self.data_dir / f"altos_raw_{call_type}_{timestamp}.json"
        with open(raw_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Raw data saved: {raw_file}")
        
        # Analyze structure
        analysis = {
            'timestamp': timestamp,
            'call_type': call_type,
            'raw_structure': self._get_structure_info(data),
            'sample_records': [],
            'field_analysis': {},
            'outbound_calls_count': 0,
            'total_calls_count': 0
        }
        
        # Extract call history
        calls = []
        if 'myphones' in data and 'callhistory' in data['myphones']:
            calls = data['myphones']['callhistory']
            analysis['total_calls_count'] = len(calls)
            
            # Filter outbound calls (direction = 'O')
            outbound_calls = [call for call in calls if call.get('d') == 'O']
            analysis['outbound_calls_count'] = len(outbound_calls)
            
            print(f"📞 Total calls found: {len(calls)}")
            print(f"📤 Outbound calls: {len(outbound_calls)}")
            
            # Analyze first few records
            sample_size = min(5, len(calls))
            for i in range(sample_size):
                call = calls[i]
                analysis['sample_records'].append(call)
                
                # Analyze fields
                for field, value in call.items():
                    if field not in analysis['field_analysis']:
                        analysis['field_analysis'][field] = {
                            'sample_values': [],
                            'data_type': type(value).__name__,
                            'description': self._guess_field_meaning(field, value)
                        }
                    
                    if len(analysis['field_analysis'][field]['sample_values']) < 3:
                        analysis['field_analysis'][field]['sample_values'].append(value)
            
            # Show sample outbound calls
            if outbound_calls:
                print("\n📋 Sample outbound calls:")
                for i, call in enumerate(outbound_calls[:3], 1):
                    calling = call.get('cg', 'Unknown')
                    called = call.get('cd', 'Unknown')
                    duration = call.get('t', 0)
                    timestamp = call.get('rs', '')
                    print(f"  {i}. {calling} → {called} | Duration: {duration}s | Time: {timestamp}")
        
        # Save analysis
        analysis_file = self.data_dir / f"altos_analysis_{call_type}_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"📊 Analysis saved: {analysis_file}")
        
        return analysis
    
    def _get_structure_info(self, data, prefix=""):
        """Recursively analyze data structure"""
        if isinstance(data, dict):
            structure = {}
            for key, value in data.items():
                structure[key] = self._get_structure_info(value, f"{prefix}.{key}")
            return structure
        elif isinstance(data, list):
            return f"Array[{len(data)} items]" + (f" - {self._get_structure_info(data[0], prefix)}" if data else "")
        else:
            return f"{type(data).__name__}: {str(data)[:50]}"
    
    def _guess_field_meaning(self, field, value):
        """Try to guess what each field means based on common patterns"""
        field_meanings = {
            'cg': 'Calling number (from)',
            'cd': 'Called number (to)', 
            'd': 'Direction (I=Inbound, O=Outbound)',
            'rs': 'Ring start timestamp',
            't': 'Talk time duration (seconds)',
            'c': 'Connected flag',
            'v': 'Voicemail flag',
            'f': 'Forwarded flag',
            'ic': 'Internal call flag',
            'co': 'Conference call flag'
        }
        
        return field_meanings.get(field, f"Unknown field - sample: {str(value)[:30]}")
    
    def test_different_date_ranges(self):
        """Test different date ranges to find what works"""
        test_dates = [
            # Yesterday
            {
                'name': 'Yesterday',
                'start': datetime.now() - timedelta(days=1),
                'end': datetime.now() - timedelta(days=1)
            },
            # Last 3 days
            {
                'name': 'Last 3 days', 
                'start': datetime.now() - timedelta(days=3),
                'end': datetime.now() - timedelta(days=1)
            },
            # Last week
            {
                'name': 'Last week',
                'start': datetime.now() - timedelta(days=7),
                'end': datetime.now() - timedelta(days=1)
            },
            # Last month (first week only due to API limits)
            {
                'name': 'Month ago (1 week)',
                'start': datetime.now() - timedelta(days=30),
                'end': datetime.now() - timedelta(days=23)
            }
        ]
        
        successful_analyses = []
        
        for test in test_dates:
            print(f"\n🗓️  Testing date range: {test['name']}")
            print(f"   From: {test['start'].strftime('%Y-%m-%d')}")
            print(f"   To: {test['end'].strftime('%Y-%m-%d')}")
            
            # Test with 'all' call types first
            url = self.build_api_url(test['start'], test['end'], 'all')
            data, error = self.make_api_request(url)
            
            if data:
                print(f"✅ Success for {test['name']}!")
                analysis = self.analyze_data_structure(data, f"all_{test['name'].replace(' ', '_')}")
                successful_analyses.append({
                    'date_range': test['name'],
                    'analysis': analysis,
                    'url': url
                })
            else:
                print(f"❌ Failed for {test['name']}: {error}")
        
        return successful_analyses
    
    def save_summary_report(self, analyses):
        """Save a comprehensive summary report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        summary = {
            'capture_timestamp': timestamp,
            'total_successful_calls': len(analyses),
            'api_window_used': f"{datetime.now().strftime('%H:%M')} (within 00:00-06:00 window)",
            'successful_date_ranges': [],
            'recommended_integration': {},
            'database_schema_suggestion': {}
        }
        
        total_outbound = 0
        best_analysis = None
        
        for analysis_data in analyses:
            analysis = analysis_data['analysis']
            summary['successful_date_ranges'].append({
                'date_range': analysis_data['date_range'],
                'total_calls': analysis['total_calls_count'],
                'outbound_calls': analysis['outbound_calls_count'],
                'url_used': analysis_data['url']
            })
            
            total_outbound += analysis['outbound_calls_count']
            
            # Use the analysis with most data for recommendations
            if not best_analysis or analysis['outbound_calls_count'] > best_analysis['outbound_calls_count']:
                best_analysis = analysis
        
        if best_analysis:
            # Generate integration recommendations
            summary['recommended_integration'] = {
                'daily_sync_time': '03:00 AM (within API window)',
                'call_type_parameter': 'all (then filter d=O for outbound)', 
                'date_range': 'Previous day only (API has 7-day limit)',
                'key_fields_for_reports': {
                    'cg': 'Calling number (sales rep phone)',
                    'cd': 'Called number (prospect/client)', 
                    'rs': 'Call timestamp',
                    't': 'Call duration (seconds)',
                    'd': 'Direction (filter for O=Outbound)'
                }
            }
            
            # Suggest database schema
            summary['database_schema_suggestion'] = {
                'table_name': 'altos_outbound_calls',
                'fields': {}
            }
            
            for field, info in best_analysis['field_analysis'].items():
                if field in ['cg', 'cd', 'rs', 't', 'd', 'c']:  # Important fields
                    summary['database_schema_suggestion']['fields'][field] = {
                        'description': info['description'],
                        'sql_type': self._suggest_sql_type(field, info['data_type'], info['sample_values'])
                    }
        
        summary['total_outbound_calls_found'] = total_outbound
        
        # Save summary
        summary_file = self.data_dir / f"ALTOS_INTEGRATION_SUMMARY_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📋 INTEGRATION SUMMARY SAVED: {summary_file}")
        print(f"🎯 Total outbound calls found across all date ranges: {total_outbound}")
        
        return summary
    
    def _suggest_sql_type(self, field, data_type, sample_values):
        """Suggest appropriate SQL column type"""
        if field == 'rs':  # timestamp
            return 'DATETIME'
        elif field == 't':  # duration
            return 'INTEGER'
        elif field in ['cg', 'cd']:  # phone numbers
            return 'VARCHAR(20)'
        elif field == 'd':  # direction
            return 'CHAR(1)'
        elif field == 'c':  # boolean flags
            return 'BOOLEAN'
        else:
            return 'TEXT'
    
    def run_overnight_capture(self):
        """Main method to run overnight data capture"""
        print("🌙 ALTOS Overnight Data Capture Starting...")
        print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait for API window if needed
        if not self.is_api_available_time():
            print("⏳ Waiting for API availability window (00:00-06:00)...")
            self.wait_for_api_window()
        
        print("🚀 Starting data capture process...")
        
        # Test different date ranges
        analyses = self.test_different_date_ranges()
        
        if analyses:
            print(f"\n✅ Successfully captured data from {len(analyses)} date ranges")
            
            # Generate summary report
            summary = self.save_summary_report(analyses)
            
            print("\n🎉 DATA CAPTURE COMPLETED!")
            print("📁 All files saved in:", self.data_dir.absolute())
            print("\n📋 NEXT STEPS:")
            print("1. Review the INTEGRATION_SUMMARY file")
            print("2. Check sample data in the raw JSON files")
            print("3. Use the field analysis to understand the data structure")
            print("4. Integrate into your existing sync system")
            
            return True
        else:
            print("\n❌ No successful API calls made")
            print("🔍 Check if API is really available during this time window")
            return False

def main():
    """Main function"""
    # Use the API token from your environment or the one you provided
    api_token = os.getenv('ALTOS_API_TOKEN', '58F22F24-3232-4490-98CE-C0B2A33A9048')
    
    print("🔑 Using API Token:", api_token[:8] + "..." + api_token[-8:])
    
    capturer = AltosDataCapturer(api_token)
    
    try:
        success = capturer.run_overnight_capture()
        
        if success:
            print("\n✅ Mission accomplished! Data structure captured.")
        else:
            print("\n❌ Mission failed. Check API availability and token.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()