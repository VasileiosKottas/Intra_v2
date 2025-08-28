#!/usr/bin/env python3
"""
ALTOS Call History API Test Script - Python Version
This script fetches outbound calls from the ALTOS API using requests library
"""

import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import argparse
import sys

class AltosAPITester:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://extprov.myphones.net/callhistory.aspx"
        
    def format_datetime(self, date_str, time_str=None):
        """Format date for API (YYYYMMDD or YYYYMMDDHHMMSS)"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted = date_obj.strftime('%Y%m%d')
            
            if time_str:
                time_obj = datetime.strptime(time_str, '%H:%M')
                formatted += time_obj.strftime('%H%M00')  # Add seconds as 00
                
            return formatted
        except ValueError as e:
            raise ValueError(f"Invalid date/time format: {e}")
    
    def validate_date_range(self, start_date, end_date):
        """Validate date range (must be <= 7 days)"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        diff_days = (end - start).days
        
        if diff_days > 7:
            raise ValueError("Date range cannot exceed 7 days")
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        if start > datetime.now():
            raise ValueError("Start date cannot be in the future")
    
    def build_api_url(self, **kwargs):
        """Build API URL with parameters"""
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        calling_filter = kwargs.get('calling_filter')
        called_filter = kwargs.get('called_filter')
        
        # Validate inputs
        self.validate_date_range(start_date, end_date)
        
        # Format dates
        sd = self.format_datetime(start_date, start_time)
        ed = self.format_datetime(end_date, end_time)
        
        print(f"🔍 Debug - Formatted start date: {sd}")
        print(f"🔍 Debug - Formatted end date: {ed}")
        
        # According to API docs, valid types are: Missed, Received, Made, All
        # Let's try 'Made' with capital M
        params = {
            'ctok': self.api_token,
            'c': 'search',
            'ty': 'Made',  # Try with capital M as per documentation
            'sd': sd,
            'ed': ed
        }
        
        # Add optional filters
        if calling_filter and len(calling_filter) >= 6:
            params['fc'] = calling_filter
            print(f"🔍 Debug - Added calling filter: {calling_filter}")
        if called_filter and len(called_filter) >= 6:
            params['fd'] = called_filter
            print(f"🔍 Debug - Added called filter: {called_filter}")
        
        print(f"🔍 Debug - All parameters: {params}")
        
        # Check if we're in core hours (API documentation mentions this restriction)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Assuming 9 AM to 5 PM are core hours
            print(f"⚠️  Warning: Current time is {current_hour}:xx - this might be during 'core hours' when API usage is restricted")
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def make_request(self, url):
        """Make HTTP GET request to API"""
        print(f"🔄 Fetching: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            print(f"📋 Response Content: {response.text[:500]}...")  # First 500 chars
            
            # Handle different HTTP status codes
            if response.status_code == 403:
                raise Exception("Invalid client token (ctok). Please check your API key.")
            elif response.status_code == 400:
                # Try to get more details from the response
                error_detail = response.text if response.text else "No additional details"
                raise Exception(f"Bad request. Server response: {error_detail}")
            elif response.status_code == 500:
                raise Exception("Server error. The API service may be temporarily unavailable.")
            elif response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.reason}. Response: {response.text}")
            
            # Parse JSON response
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                # If JSON parsing fails, maybe it's not JSON
                print(f"⚠️  Response is not JSON. Content: {response.text}")
                raise Exception(f"Invalid JSON response from API. Content: {response.text}")
            
        except requests.exceptions.Timeout:
            raise Exception("Request timeout. The API may be slow to respond.")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        except Exception as e:
            if "Bad request" in str(e) or "Invalid JSON" in str(e):
                raise  # Re-raise our custom exceptions
            raise Exception(f"Unexpected error: {e}")
    
    def format_readable_datetime(self, timestamp):
        """Convert API timestamp to readable format"""
        if not timestamp or len(timestamp) < 8:
            return "Unknown"
        
        try:
            year = timestamp[:4]
            month = timestamp[4:6]
            day = timestamp[6:8]
            hour = timestamp[8:10] if len(timestamp) >= 10 else "00"
            minute = timestamp[10:12] if len(timestamp) >= 12 else "00"
            second = timestamp[12:14] if len(timestamp) >= 14 else "00"
            
            return f"{year}-{month}-{day} {hour}:{minute}:{second}"
        except:
            return "Invalid timestamp"
    
    def format_duration(self, seconds):
        """Convert seconds to MM:SS format"""
        if not seconds:
            return "N/A"
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes}:{secs:02d}"
    
    def analyze_calls(self, data):
        """Analyze and display call data"""
        if not data or 'myphones' not in data or 'callhistory' not in data['myphones']:
            print("❌ No call history data found in response")
            return
        
        calls = data['myphones']['callhistory']
        total_calls = len(calls)
        
        if total_calls == 0:
            print("📞 No outbound calls found in the specified date range")
            return
        
        # Calculate statistics
        answered_calls = sum(1 for call in calls if call.get('c'))
        total_duration = sum(call.get('t', 0) for call in calls)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        # Display statistics
        print(f"\n📊 OUTBOUND CALL STATISTICS")
        print(f"{'='*50}")
        print(f"Total Calls: {total_calls}")
        print(f"Answered: {answered_calls}")
        print(f"Not Answered: {total_calls - answered_calls}")
        print(f"Answer Rate: {(answered_calls/total_calls)*100:.1f}%")
        print(f"Total Duration: {self.format_duration(total_duration)}")
        print(f"Average Duration: {self.format_duration(avg_duration)}")
        
        # Display individual calls
        print(f"\n📞 CALL DETAILS")
        print(f"{'='*50}")
        
        for i, call in enumerate(calls, 1):
            call_time = self.format_readable_datetime(call.get('rs', ''))
            calling_num = call.get('cg', 'Unknown')
            called_num = call.get('cd', 'Unknown')
            duration = self.format_duration(call.get('t', 0))
            answered = "✅ Answered" if call.get('c') else "❌ Not Answered"
            
            print(f"\nCall #{i}")
            print(f"  📞 {calling_num} → {called_num}")
            print(f"  🕐 Time: {call_time}")
            print(f"  ⏱️  Duration: {duration}")
            print(f"  📋 Status: {answered}")
            
            # Additional call details
            details = []
            if call.get('v'):
                details.append("📧 Voicemail")
            if call.get('f'):
                details.append("↪️ Transferred")
            if call.get('ic'):
                details.append("🏢 Internal")
            if call.get('co'):
                details.append("👥 Conference")
            
            if details:
                print(f"  ℹ️  Notes: {', '.join(details)}")
    
    def test_api(self, **kwargs):
        """Main test function"""
        try:
            url = self.build_api_url(**kwargs)
            data = self.make_request(url)
            
            print("✅ API request successful!")
            self.analyze_calls(data)
            
            # Save raw response to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"altos_api_response_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\n💾 Raw response saved to: {filename}")
            return data
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Test ALTOS Call History API for outbound calls')
    
    parser.add_argument('--token', required=True, help='API authentication token')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--start-time', help='Start time (HH:MM)')
    parser.add_argument('--end-time', help='End time (HH:MM)')
    parser.add_argument('--calling-filter', help='Filter by calling number (min 6 digits)')
    parser.add_argument('--called-filter', help='Filter by called number (min 6 digits)')
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = AltosAPITester(args.token)
    
    # Test API with provided parameters
    tester.test_api(
        start_date=args.start_date,
        end_date=args.end_date,
        start_time=args.start_time,
        end_time=args.end_time,
        calling_filter=args.calling_filter,
        called_filter=args.called_filter
    )

def test_exact_example():
    """Test using the exact parameters from the original documentation"""
    API_TOKEN = "58F22F24-3232-4490-98CE-C0B2A33A9048"
    
    print("🔍 Testing with EXACT parameters from documentation example...")
    print("Original example: ty=all&sd=20160601&ed=20160713124500")
    print("=" * 60)
    
    # Test different date formats based on the original example
    test_cases = [
        {
            'name': 'Exact format from docs (with time)',
            'params': {
                'ctok': API_TOKEN,
                'c': 'search',
                'ty': 'all',
                'sd': '20250521',
                'ed': '20250713124500'  # End of day with time
            }
        },
        {
            'name': 'Date only format',
            'params': {
                'ctok': API_TOKEN,
                'c': 'search', 
                'ty': 'all',
                'sd': '20250821',
                'ed': '20250821'
            }
        },
        {
            'name': 'Much older date (2024)',
            'params': {
                'ctok': API_TOKEN,
                'c': 'search',
                'ty': 'all', 
                'sd': '20240821',
                'ed': '20240821'
            }
        },
        {
            'name': 'Test with different token format',
            'params': {
                'ctok': API_TOKEN.replace('-', ''),  # Remove dashes
                'c': 'search',
                'ty': 'all',
                'sd': '20250821', 
                'ed': '20250821'
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n🧪 {test['name']}")
        try:
            url = f"https://extprov.myphones.net/callhistory.aspx?{urlencode(test['params'])}"
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=15)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS!")
                try:
                    data = response.json()
                    calls = data.get('myphones', {}).get('callhistory', [])
                    print(f"   📞 Found {len(calls)} calls")
                    return True
                except:
                    print(f"   📄 Response content: {response.text[:200]}...")
            else:
                print(f"   ❌ Failed: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return False

def test_token_validation():
    """Test if the token itself is valid"""
    API_TOKEN = "58F22F24-3232-4490-98CE-C0B2A33A9048"
    
    print("🔑 Testing token validation...")
    print("=" * 40)
    
    # Test with minimal required parameters only
    minimal_params = {
        'ctok': API_TOKEN,
        'c': 'search'  # Just these two required params
    }
    
    try:
        url = f"https://extprov.myphones.net/callhistory.aspx?{urlencode(minimal_params)}"
        print(f"🔄 Testing minimal params: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 403:
            print("❌ Token is invalid or expired")
            return False
        elif response.status_code == 400:
            print("✅ Token is valid (400 means missing required params)")
            return True
        else:
            print(f"? Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def check_api_status():
    """Check if the API endpoint is accessible at all"""
    print("🌐 Checking API endpoint accessibility...")
    print("=" * 40)
    
    try:
        # Just hit the base URL to see if it responds
        response = requests.get("https://extprov.myphones.net/", timeout=10)
        print(f"Base domain status: {response.status_code}")
        
        response = requests.get("https://extprov.myphones.net/callhistory.aspx", timeout=10)
        print(f"API endpoint status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        return response.status_code in [400, 403, 200]  # Any of these means it's responding
        
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        return False

def test_with_older_date():
    """Test with a date from a week ago to avoid core hours issues"""
    API_TOKEN = "58F22F24-3232-4490-98CE-C0B2A33A9048"
    
    # Try a week ago
    week_ago = datetime.now() - timedelta(days=7)
    test_date = week_ago.strftime('%Y-%m-%d')
    
    print(f"\n🔄 Testing with older date: {test_date}")
    print("This might avoid core hours restrictions...")
    
    try:
        tester = AltosAPITester(API_TOKEN)
        
        # Test with 'all' first since the original documentation used that
        params = {
            'ctok': API_TOKEN,
            'c': 'search',
            'ty': 'all',
            'sd': test_date.replace('-', ''),
            'ed': test_date.replace('-', '')
        }
        
        url = f"https://extprov.myphones.net/callhistory.aspx?{urlencode(params)}"
        print(f"🔄 Fetching: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"📋 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            calls = data.get('myphones', {}).get('callhistory', [])
            print(f"✅ SUCCESS! Found {len(calls)} calls")
            
            # Filter for outbound calls manually
            outbound_calls = [call for call in calls if call.get('d') == 'O']
            print(f"📞 Outbound calls: {len(outbound_calls)}")
            
            if outbound_calls:
                print("🎯 WORKING SOLUTION FOUND!")
                print("You can use ty='all' and then filter for direction='O' in your code")
                return True
        else:
            print(f"❌ Still failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def test_different_parameters():
    """Test different parameter combinations to find what works"""
    API_TOKEN = "58F22F24-3232-4490-98CE-C0B2A33A9048"
    
    # Use a smaller date range (yesterday only to avoid current day issues)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🧪 Testing different parameter combinations for {yesterday}")
    print(f"⏰ Current time: {datetime.now().strftime('%H:%M')} - Core hours restriction may apply")
    print("=" * 60)
    
    # Test different call types as per API documentation
    call_types_to_test = [
        ('all', 'All call types'),
        ('made', 'Outbound calls (lowercase)'),
        ('Made', 'Outbound calls (capitalized)'),
        ('received', 'Inbound calls (lowercase)'),
        ('Received', 'Inbound calls (capitalized)'),
        ('missed', 'Missed calls'),
        ('Missed', 'Missed calls (capitalized)')
    ]
    
    for call_type, description in call_types_to_test:
        print(f"\n🔍 Testing: {description} (ty={call_type})")
        
        try:
            # Build URL manually for this test
            params = {
                'ctok': API_TOKEN,
                'c': 'search',
                'ty': call_type,
                'sd': "20250601",
                'ed': "20250713124500"
            }
            
            url = f"https://extprov.myphones.net/callhistory.aspx?{urlencode(params)}"
            print(f"   URL: {url}")
            
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS! This parameter works")
                try:
                    data = response.json()
                    call_count = len(data.get('myphones', {}).get('callhistory', []))
                    print(f"   📞 Found {call_count} calls")
                    
                    # Show first call as example
                    if call_count > 0:
                        first_call = data['myphones']['callhistory'][0]
                        direction = "Outbound" if first_call.get('d') == 'O' else "Inbound" if first_call.get('d') == 'I' else "Unknown"
                        print(f"   📋 Sample: {direction} call from {first_call.get('cg', 'Unknown')} to {first_call.get('cd', 'Unknown')}")
                        
                        # If this worked and has outbound calls, save the working parameters
                        if call_type in ['made', 'Made', 'all'] and call_count > 0:
                            print(f"   🎯 RECOMMENDED: Use ty={call_type} for outbound calls")
                    
                    return call_type  # Return the working call type
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️  Response not JSON: {response.text[:100]}...")
                    
            elif response.status_code == 400:
                print(f"   ❌ Bad Request: {response.text[:100]}...")
            elif response.status_code == 403:
                print(f"   ❌ Forbidden: Invalid token")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return None

def test_with_older_date():
    """Test with a date from a week ago to avoid core hours issues"""
    API_TOKEN = "58F22F24-3232-4490-98CE-C0B2A33A9048"
    
    # Try a week ago
    week_ago = datetime.now() - timedelta(days=7)
    test_date = week_ago.strftime('%Y-%m-%d')
    
    print(f"\n🔄 Testing with older date: {test_date}")
    print("This might avoid core hours restrictions...")
    
    try:
        # Test with 'all' first since the original documentation used that
        params = {
            'ctok': API_TOKEN,
            'c': 'search',
            'ty': 'all',
            'sd': "20250601",
            'ed': "20250713124500"
        }
        
        url = f"https://extprov.myphones.net/callhistory.aspx?{urlencode(params)}"
        print(f"🔄 Fetching: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"📋 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            calls = data.get('myphones', {}).get('callhistory', [])
            print(f"✅ SUCCESS! Found {len(calls)} calls")
            
            # Filter for outbound calls manually
            outbound_calls = [call for call in calls if call.get('d') == 'O']
            print(f"📞 Outbound calls: {len(outbound_calls)}")
            
            if outbound_calls:
                print("🎯 WORKING SOLUTION FOUND!")
                print("You can use ty='all' and then filter for direction='O' in your code")
                return True
        else:
            print(f"❌ Still failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def quick_test():
    """Quick test with comprehensive debugging"""
    print("🚀 ALTOS API Comprehensive Diagnostic")
    print("=" * 50)
    
    # Test 1: Check API accessibility
    print("STEP 1: API Accessibility Check")
    accessible = check_api_status()
    if not accessible:
        print("❌ API endpoint is not accessible. Stopping tests.")
        return
    
    # Test 2: Test token validation
    print("\nSTEP 2: Token Validation")
    token_valid = test_token_validation()
    if not token_valid:
        print("❌ Token appears to be invalid. Please check your API key.")
        return
    
    print("✅ Token appears to be valid")
    
    # Test 3: Try exact format from documentation
    print("\nSTEP 3: Testing Exact Documentation Format")
    success = test_exact_example()
    
    if success:
        print("\n🎯 SUCCESS! Found working parameters")
    else:
        print("\n❌ All tests failed")
        print("\n🔍 POSSIBLE ISSUES:")
        print("1. ⏰ Core hours restriction (try after 5 PM or weekends)")
        print("2. 🗓️  Date restrictions (API might not have data for these dates)")
        print("3. 🔑 Token permissions (token might be read-only or restricted)")
        print("4. 🏢 Account status (account might be inactive/suspended)")
        print("5. 🌐 IP restrictions (API might be restricted to certain IP addresses)")
        
        print("\n📞 NEXT STEPS:")
        print("• Contact Paul or the API provider to verify:")
        print("  - Token is active and has correct permissions")
        print("  - Account status is active") 
        print("  - No IP address restrictions")
        print("  - What the actual core hours are")
        print("• Try running this script after 5 PM or on weekends")
        print("• Ask for a working example URL with current date")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run quick test if no arguments provided
        quick_test()
    else:
        # Run with command line arguments
        main()