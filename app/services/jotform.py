"""
Enhanced JotForm API integration service with income_type field and improved name matching
FIXED: Uses query parameter authentication like the working curl command
"""

import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from app.config import config_manager

class JotFormService:
    """Service for JotForm API integration"""
    
    def __init__(self, company: str):
        self.company = company
        self.config = config_manager.get_company_config(company)
        
        # Get API key from config
        self.api_key = config_manager.get_app_config('JOTFORM_API_KEY')
        self.base_url = config_manager.get_app_config('BASE_URL')
        self.submission_form_id = config_manager.get_app_config('SUBMISSION_FORM_ID')
        self.paid_form_id = config_manager.get_app_config('PAID_FORM_ID')
        
        # FIXED: Remove APIKEY header - we'll use query parameters instead
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "PythonJotFormClient/1.0"
        }
        
        # Field mappings
        self.submission_field_map = {
            'advisor_name': '39',
            'business_type': '3',
            'submission_date': '6',
            'customer_name': '7',
            'expected_proc': '12',
            'expected_fee': '13',
        }
        
        self.paid_field_map = {
            'advisor_name': '5',
            'who_referred': '9',
            'case_type': '8',
            'value': '12',
            'customer_name': '4',
            'date_paid': '13',
            'income_type': '6'  # NEW: Add income_type to paid cases too
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        self.max_retries = 3
        
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            print(f"⏳ Rate limiting: waiting {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, additional_params: Optional[Dict] = None) -> Optional[Dict]:
        """FIXED: Make request using query parameter authentication (like working curl)"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                # Wait for rate limit
                self._wait_for_rate_limit()
                
                # FIXED: Use query parameter authentication (like curl)
                params = {
                    "apiKey": self.api_key  # This matches your working curl: ?apiKey={apiKey}
                }
                
                # Add any additional parameters
                if additional_params:
                    params.update(additional_params)
                
                print(f"🔄 Making API request (attempt {attempt + 1}/{self.max_retries}): {endpoint}")
                print(f"📡 URL: {url}")
                print(f"📋 Params: {list(params.keys())}")  # Don't print API key value
                
                # FIXED: No headers authentication, use params instead
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                print(f"📊 Status: {response.status_code}")
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"⚠️ Rate limit hit! Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Show API limit info if available
                    if isinstance(data, dict) and 'limit-left' in data:
                        print(f"🔋 API calls remaining: {data['limit-left']}")
                    
                    return data
                else:
                    print(f"❌ Error {response.status_code}: {response.text}")
                    if attempt == self.max_retries - 1:
                        return None
                
            except requests.exceptions.RequestException as e:
                print(f"❌ API request failed (attempt {attempt + 1}): {str(e)}")
                
                if attempt == self.max_retries - 1:
                    print(f"💥 All {self.max_retries} attempts failed")
                    return None
                
                # Exponential backoff for retries
                wait_time = (2 ** attempt) * 5  # 5, 10, 20 seconds
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        return None
    
    def _parse_date(self, date_string) -> Optional[datetime.date]:
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
            print(f"⚠️ Error parsing date '{date_string}': {e}")
            return None
    
    def get_form_submissions_with_mapping(self, form_id: str, field_map: Dict, limit: int = 1000) -> List[Dict]:
        """Get form submissions using exact field mappings with rate limiting"""
        print(f"📋 Fetching submissions for form {form_id} (Company: {self.company})...")
        
        endpoint = f"/form/{form_id}/submissions"
        additional_params = {
            "limit": limit,
            "orderby": "submission_date"  # Add ordering for consistency
        }
        
        response = self._make_request(endpoint, additional_params)
        
        if not response:
            print("❌ Failed to get response from JotForm API")
            return []
        
        # Handle JotForm response format
        if response.get('responseCode') != 200:
            print(f"❌ JotForm API error: {response.get('message', 'Unknown error')}")
            return []
        
        submissions = response.get("content", [])
        print(f"✅ Retrieved {len(submissions)} raw submissions")
        
        parsed_submissions = []
        
        for submission in submissions:
            parsed_data = {
                "submission_id": submission.get("id"),
                "created_at": submission.get("submission_date"),
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
    
    def test_connection(self) -> bool:
        """Test the API connection"""
        print("🧪 Testing JotForm API connection...")
        
        # Test getting form info (like your working curl)
        endpoint = f"/form/{self.submission_form_id}"
        result = self._make_request(endpoint)
        
        if result and result.get('responseCode') == 200:
            content = result.get('content', {})
            print(f"✅ Form: {content.get('title', 'Unknown')}")
            print(f"✅ Status: {content.get('status', 'Unknown')}")
            print(f"✅ Total submissions: {content.get('count', 'Unknown')}")
            print(f"✅ Last submission: {content.get('last_submission', 'Unknown')}")
            return True
        else:
            print("❌ Connection test failed")
            return False
            
    def process_submissions(self) -> List[Dict]:
        """Process submissions - CAPTURE ALL referrals regardless of type"""
        print(f"📄 Processing submissions from JotForm for {self.company}...")
        
        submissions_data = self.get_form_submissions_with_mapping(
            self.submission_form_id, 
            self.submission_field_map
        )
        
        if not submissions_data:
            print("📄 No submissions data retrieved")
            return []
        
        processed_submissions = []
        
        for submission in submissions_data:
            try:
                data = submission.get("mapped_data", {})
                
                advisor_name = self.config.normalize_advisor_name(data.get("advisor_name", ""))
                business_type = str(data.get("business_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                income_type = str(data.get("income_type", ""))
                
                # Store original business type BEFORE any changes
                original_business_type = business_type
                
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
                
                submission_date = self._parse_date(data.get("submission_date", ""))
                if not submission_date:
                    submission_date = self._parse_date(submission.get("submission_date", ""))
                
                # Check if this is ANY kind of referral
                referral_to = None
                is_referral = 'referral' in business_type.lower()
                
                if is_referral:
                    print(f"Found referral: '{original_business_type}'")
                    
                    # Extract referral_to for "Referral to X" format
                    if 'referral to' in business_type.lower():
                        referral_to = business_type.lower().split('referral to')[-1].strip().title()
                    
                    # Set business_type to 'Referral' for consistent database storage
                    business_type = 'Referral'
                
                # SAVE CONDITIONS: Valid business type OR any referral
                should_save = False
                if advisor_name:
                    if is_referral:
                        should_save = True  # Save ALL referrals
                        print(f"Saving referral: {original_business_type}")
                    elif self.config.is_valid_business_type(business_type):
                        should_save = True  # Save other valid types
                
                if should_save:
                    processed_submissions.append({
                        'advisor_name': advisor_name,
                        'business_type': business_type,
                        'original_business_type': original_business_type,
                        'submission_date': submission_date or datetime.now().date(),
                        'customer_name': customer_name,
                        'expected_proc': expected_proc,
                        'expected_fee': expected_fee,
                        'referral_to': referral_to,
                        'income_type': income_type,
                        'company': self.company,
                        'jotform_id': submission.get("submission_id")
                    })
                    
            except Exception as e:
                print(f"Error processing submission: {e}")
                continue
        
        print(f"Successfully processed {len(processed_submissions)} submissions for {self.company}")
        return processed_submissions

    def process_paid_cases(self) -> List[Dict]:
        """Process paid cases with company-specific filtering and enhanced name matching"""
        print(f"💰 Processing paid cases from JotForm for {self.company}...")
        
        paid_data = self.get_form_submissions_with_mapping(
            self.paid_form_id, 
            self.paid_field_map
        )
        
        if not paid_data:
            print("💰 No paid cases data retrieved")
            return []
        
        processed_cases = []

        for case in paid_data:
            try:
                data = case.get("mapped_data", {})
                
                # FIXED: Handle None values safely for all string fields
                advisor_name = self.config.normalize_advisor_name(data.get("advisor_name") or "")
                case_type = str(data.get("case_type") or "")
                customer_name = str(data.get("customer_name") or "Unknown Customer")
                income_type = str(data.get("income_type") or "")
                
                # ENHANCED: Extract who_referred field with improved normalization
                who_referred_raw = data.get("who_referred")  # Don't convert to string yet
                who_referred = self._normalize_referrer_name(who_referred_raw)
                
                try:
                    value_raw = data.get("value")
                    if value_raw and str(value_raw) != "No Answer":
                        # Handle negative values properly
                        value_str = str(value_raw).replace('£', '').replace(',', '').strip()
                        value = float(value_str or 0)
                    else:
                        value = 0
                except (ValueError, TypeError):
                    value = 0
                
                date_paid = self._parse_date(data.get("date_paid"))
                if not date_paid:
                    date_paid = self._parse_date(case.get("submission_date"))
                
                # Company-specific filtering
                if (advisor_name and 
                    self.config.is_valid_paid_case_type(case_type) and 
                    value != 0):
                
                    processed_cases.append({
                        'advisor_name': advisor_name,
                        'case_type': case_type,
                        'value': value,
                        'customer_name': customer_name,
                        'date_paid': date_paid or datetime.now().date(),
                        'who_referred': who_referred,
                        'income_type': income_type,
                        'company': self.company,
                        'jotform_id': case.get("submission_id")
                    })
            except Exception as e:
                # IMPROVED: Show which field caused the error
                print(f"💰 Error processing paid case {case.get('submission_id', 'unknown')}: {e}")
                
                # DEBUG: Show the problematic data
                if hasattr(e, '__class__') and 'NoneType' in str(e):
                    print(f"   Debug - Raw data: {case.get('mapped_data', {})}")
                continue
        
        print(f"💰 Successfully processed {len(processed_cases)} valid paid cases for {self.company}")
        return processed_cases

    def _normalize_referrer_name(self, who_referred_raw):
        """
        ENHANCED: Normalize the referrer name using company mappings
        FIXED: Handle None values properly
        """
        # FIXED: Check for None first before any string operations
        if who_referred_raw is None:
            return None
        
        # FIXED: Convert to string safely and strip
        try:
            who_referred_clean = str(who_referred_raw).strip()
        except (AttributeError, TypeError):
            # Handle edge cases where conversion fails
            return None
        
        # Check for empty or "no answer" values
        if not who_referred_clean or who_referred_clean.lower() in ["no answer", "none", "", "null"]:
            return None
        
        # Use company config to normalize the name
        normalized_name = self.config.normalize_advisor_name(who_referred_clean)
        
        # If normalization returns a valid advisor name, use it
        if normalized_name and normalized_name in self.config.advisor_names:
            print(f"   Normalized '{who_referred_raw}' → '{normalized_name}'")
            return normalized_name
        
        # Otherwise return the original clean value
        return who_referred_clean