import requests
import time
import json
from datetime import datetime
from typing import List, Dict, Optional

class EUJotFormService:
    """JotForm service configured for EU Safe mode accounts"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # IMPORTANT: Use EU endpoint for EU accounts
        self.base_url = "https://eu-api.jotform.com"
        self.headers = {
            "APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Conservative rate limiting
        self.last_request_time = 0
        self.min_request_interval = 3.0  # 3 seconds between requests
        self.request_count = 0
        self.hourly_limit = 90  # Conservative limit for free accounts
        
    def _wait_for_rate_limit(self):
        """Wait between requests to avoid rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            print(f"⏳ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make request to EU JotForm API"""
        
        # Check hourly limit
        if self.request_count >= self.hourly_limit:
            print(f"🛑 Reached hourly limit ({self.hourly_limit}). Stopping requests.")
            return None
        
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.request_count += 1
            print(f"📡 EU API Request #{self.request_count}: {endpoint}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 429:
                print("🚫 Rate limited! Stopping all requests.")
                return None
            
            if response.status_code == 301 or response.status_code == 302:
                print("🔄 Redirect detected - this shouldn't happen with EU endpoint")
                return None
                
            if response.status_code != 200:
                print(f"❌ Error {response.status_code}: {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test EU API connection"""
        print("🔍 Testing EU JotForm API connection...")
        
        result = self._make_request("/user")
        if result:
            content = result.get('content', {})
            if content:  # Should have data now
                print(f"✅ Connected as: {content.get('name', 'User')}")
                print(f"📧 Email: {content.get('email', 'N/A')}")
                print(f"📋 Account: {content.get('accountType', 'N/A')}")
                return True
            else:
                print("⚠️ Connected but no user data returned")
                return False
        else:
            print("❌ Connection test failed")
            return False
    
    def get_usage_info(self) -> Optional[Dict]:
        """Get API usage information"""
        print("📊 Checking EU API usage...")
        
        result = self._make_request("/user/usage")
        if result:
            content = result.get('content', {})
            
            if content:
                print("📈 Usage Information:")
                print(json.dumps(content, indent=2))
                
                # Look for API usage info
                if 'apiCalls' in content:
                    api_info = content['apiCalls']
                    used = api_info.get('used', 0)
                    limit = api_info.get('limit', 100)
                    remaining = limit - used
                    
                    print(f"🔋 API Calls: {used}/{limit} (Remaining: {remaining})")
                    
                    if remaining < 20:
                        print("⚠️ WARNING: Less than 20 API calls remaining!")
                
                return content
            else:
                print("⚠️ No usage data available")
                
        return None
    
    def get_forms_list(self, limit: int = 20) -> Optional[List[Dict]]:
        """Get list of forms from EU API"""
        print(f"📋 Fetching forms list (limit: {limit})...")
        
        result = self._make_request("/user/forms", {"limit": limit})
        
        if result:
            forms = result.get('content', [])
            print(f"✅ Found {len(forms)} forms")
            
            for i, form in enumerate(forms[:5], 1):  # Show first 5
                form_id = form.get('id', 'N/A')
                title = form.get('title', 'Untitled')
                status = form.get('status', 'N/A')
                print(f"  {i}. [{form_id}] {title} ({status})")
            
            if len(forms) > 5:
                print(f"  ... and {len(forms) - 5} more forms")
                
            return forms
        
        return None
    
    def get_form_submissions(self, form_id: str, limit: int = 50) -> Optional[List[Dict]]:
        """Get submissions from a specific form"""
        print(f"📥 Fetching submissions for form {form_id} (limit: {limit})")
        
        result = self._make_request(f"/form/{form_id}/submissions", {"limit": limit})
        
        if result:
            submissions = result.get('content', [])
            print(f"✅ Retrieved {len(submissions)} submissions")
            
            if submissions:
                print("📋 Sample submission structure:")
                sample = submissions[0]
                print(f"  - ID: {sample.get('id')}")
                print(f"  - Created: {sample.get('created_at')}")
                print(f"  - Status: {sample.get('status')}")
                print(f"  - Answers: {len(sample.get('answers', {}))} fields")
                
            return submissions
            
        return None
    
    def get_form_questions(self, form_id: str) -> Optional[Dict]:
        """Get form structure to understand field mappings"""
        print(f"❓ Getting form questions for {form_id}...")
        
        result = self._make_request(f"/form/{form_id}/questions")
        
        if result:
            questions = result.get('content', {})
            print(f"✅ Found {len(questions)} questions/fields")
            
            print("\n📋 Form Field Structure:")
            for q_id, question in list(questions.items())[:10]:  # First 10 fields
                q_type = question.get('type', 'unknown')
                q_text = question.get('text', 'No text')
                q_name = question.get('name', 'No name')
                print(f"  [{q_id}] {q_type}: {q_text[:50]}{'...' if len(q_text) > 50 else ''}")
                if q_name != 'No name':
                    print(f"        Name: {q_name}")
            
            if len(questions) > 10:
                print(f"  ... and {len(questions) - 10} more fields")
                
            return questions
            
        return None

# Test script
def test_eu_jotform():
    """Test the EU JotForm service"""
    API_KEY = "b78b083ca0a78392acf8de69666a3577"
    
    print("🇪🇺 Testing EU JotForm API Service")
    print("=" * 50)
    
    service = EUJotFormService(API_KEY)
    
    # Test 1: Connection
    if not service.test_connection():
        print("❌ Connection failed - stopping tests")
        return
    
    print("\n" + "="*40)
    
    # Test 2: Usage
    service.get_usage_info()
    
    print("\n" + "="*40)
    
    # Test 3: Forms
    forms = service.get_forms_list()
    
    # If we have forms and API calls remaining, test submissions
    if forms and service.request_count < service.hourly_limit - 5:
        print("\n" + "="*40)
        
        # Test with first form
        first_form = forms[0]
        form_id = first_form.get('id')
        
        if form_id:
            print(f"📋 Testing submissions for form: {first_form.get('title', form_id)}")
            
            # Get form structure first
            service.get_form_questions(form_id)
            
            print("\n" + "-"*30)
            
            # Get submissions
            submissions = service.get_form_submissions(form_id, limit=5)
            
    print(f"\n📊 Total EU API calls used: {service.request_count}")
    print("✅ EU API test completed")

if __name__ == "__main__":
    test_eu_jotform()