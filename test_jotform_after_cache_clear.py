import requests
import time
import json

def test_jotform_after_cache_clear():
    """Test JotForm API after cache clearing to see if 429 errors are resolved"""
    
    print("🧪 TESTING JOTFORM API AFTER CACHE CLEAR")
    print("=" * 55)
    
    API_KEY = "6aa5460625d72bc50847166d93099640"
    
    # Use fresh headers with cache-busting
    headers = {
        "APIKEY": API_KEY,
        "User-Agent": "PostCacheClear-Test/1.0",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    # Test both endpoints to see which works
    endpoints_to_test = [
        ("EU API (Recommended)", "https://eu-api.jotform.com"),
        ("US API (Fallback)", "https://api.jotform.com")
    ]
    
    for name, base_url in endpoints_to_test:
        print(f"\n🔍 Testing {name}: {base_url}")
        print("-" * 50)
        
        # Add timestamp to prevent any caching
        test_url = f"{base_url}/user?_t={int(time.time())}&_test=postcache"
        
        try:
            print(f"📡 Making request to: /user")
            print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            start_time = time.time()
            response = requests.get(test_url, headers=headers, timeout=15)
            response_time = time.time() - start_time
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📊 Response Time: {response_time:.2f} seconds")
            
            # Check response headers for clues
            interesting_headers = ['retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset']
            found_headers = False
            for header in interesting_headers:
                if header in response.headers:
                    print(f"📊 {header}: {response.headers[header]}")
                    found_headers = True
            
            if response.status_code == 200:
                print("🎉 SUCCESS! Cache clearing appears to have worked!")
                
                try:
                    data = response.json()
                    content = data.get('content', {})
                    
                    if content:
                        print(f"✅ Account Name: {content.get('name', 'N/A')}")
                        print(f"✅ Email: {content.get('email', 'N/A')}")
                        print(f"✅ Account Type: {content.get('accountType', 'N/A')}")
                        print(f"✅ Status: {content.get('status', 'N/A')}")
                        print(f"✅ API Key Working: YES")
                        
                        # Try to get forms list if user endpoint worked
                        print(f"\n📋 Testing forms list...")
                        forms_url = f"{base_url}/user/forms?limit=5&_t={int(time.time())}"
                        forms_response = requests.get(forms_url, headers=headers, timeout=10)
                        
                        if forms_response.status_code == 200:
                            forms_data = forms_response.json()
                            forms = forms_data.get('content', [])
                            print(f"✅ Forms accessible: {len(forms)} forms found")
                            
                            if forms:
                                print("📄 Available forms:")
                                for i, form in enumerate(forms[:3], 1):
                                    print(f"   {i}. [{form.get('id')}] {form.get('title', 'Untitled')}")
                        elif forms_response.status_code == 429:
                            print("❌ Forms still rate limited - but user endpoint worked!")
                        else:
                            print(f"⚠️ Forms returned {forms_response.status_code}")
                        
                        return True, base_url
                    else:
                        print("⚠️ Success but empty content")
                        return False, None
                        
                except json.JSONDecodeError:
                    print("⚠️ Success but invalid JSON response")
                    return False, None
                    
            elif response.status_code == 429:
                print("❌ Still getting 429 - cache clearing didn't resolve the issue")
                print(f"Response: {response.text}")
                
                if 'Retry-After' in response.headers:
                    retry_after = response.headers['Retry-After']
                    print(f"🔄 Retry-After: {retry_after} seconds")
                    
            elif response.status_code == 301 or response.status_code == 302:
                redirect_location = response.headers.get('Location', 'Unknown')
                print(f"🔄 Redirected to: {redirect_location}")
                
                if 'eu-api' in redirect_location and 'eu-api' not in base_url:
                    print("💡 You should use the EU endpoint: https://eu-api.jotform.com")
                    
            else:
                print(f"❓ Unexpected status: {response.status_code}")
                print(f"Response preview: {response.text[:200]}...")
            
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except requests.exceptions.ConnectionError:
            print("🌐 Connection error - check internet connection")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return False, None

def test_specific_form_data(base_url, api_key):
    """Test accessing your specific forms"""
    
    print(f"\n📋 TESTING YOUR SPECIFIC FORMS")
    print("=" * 40)
    
    headers = {
        "APIKEY": api_key,
        "Cache-Control": "no-cache"
    }
    
    # Your form IDs from the config
    form_ids = {
        "Submission Form": "250232251408041",
        "Paid Form": "251406545360048"
    }
    
    for form_name, form_id in form_ids.items():
        print(f"\n🔍 Testing {form_name} ({form_id})...")
        
        # Test form submissions with very small limit
        submissions_url = f"{base_url}/form/{form_id}/submissions"
        params = {"limit": 5}  # Very small limit
        
        try:
            response = requests.get(submissions_url, headers=headers, params=params, timeout=10)
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                submissions = data.get('content', [])
                print(f"✅ {len(submissions)} submissions retrieved")
                
                if submissions:
                    print(f"📄 Latest submission: {submissions[0].get('created_at', 'N/A')}")
                    
            elif response.status_code == 429:
                print("❌ Still rate limited on form data")
            else:
                print(f"⚠️ Unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing form: {e}")
        
        # Small delay between form tests
        time.sleep(2)

if __name__ == "__main__":
    print("Testing JotForm API after cache clearing...")
    print("This will help determine if the 429 errors are resolved")
    print()
    
    success, working_endpoint = test_jotform_after_cache_clear()
    
    if success:
        print(f"\n🎉 GREAT NEWS!")
        print("=" * 30)
        print("✅ Cache clearing resolved your 429 errors!")
        print(f"✅ Working endpoint: {working_endpoint}")
        print("✅ Your JotForm API is now functional")
        
        # Test form data access
        API_KEY = "b78b083ca0a78392acf8de69666a3577"
        test_specific_form_data(working_endpoint, API_KEY)
        
        print(f"\n💡 NEXT STEPS:")
        print("1. Update your JotForm service to use the working endpoint")
        print("2. Add conservative rate limiting (3-5 seconds between calls)")
        print("3. Test your application's sync functionality")
        
    else:
        print(f"\n😔 CACHE CLEARING DIDN'T RESOLVE IT")
        print("=" * 45)
        print("❌ Still getting 429 errors after cache clearing")
        print("💡 This confirms it's a server-side issue")
        print()
        print("🎯 IMMEDIATE ACTION REQUIRED:")
        print("1. Send the support email to JotForm immediately")
        print("2. Ask them to clear your SERVER-SIDE form cache")
        print("3. Request IP whitelisting")
        print("4. Ask them to verify/reset your daily API limits")
        print()
        print("📧 Use the email template I provided earlier")
        print("🔗 Send to: support@jotform.com")
        print("⚠️ Mention: 'Persistent 429 errors even after cache clearing'")
