#!/usr/bin/env python3
"""
Test Full Sync Process - Complete simulation of the sync process
"""

import requests
from datetime import datetime

class TestDataManager:
    """Test version of DataManager to debug sync process"""
    
    SUBMISSION_FORM_ID = "250232251408041"
    PAID_FORM_ID = "251406545360048"
    BASE_URL = "https://eu-api.jotform.com"
    
    # Corrected field mappings
    SUBMISSION_FIELD_MAP = {
        'advisor_name': '39',       # Question 39: Advisor name (dropdown)
        'business_type': '3',       # Question 3: What type of business are you submitting?
        'submission_date': '6',     # Question 6: Date
        'customer_name': '7',       # Question 7: Customer Name(s)
        'expected_proc': '12',      # Question 12: Expected Proc
        'expected_fee': '13'        # Question 13: Expected Fee
    }
    
    PAID_FIELD_MAP = {
        'advisor_name': '5',        # Question 5: Advisor Name
        'case_type': '8',           # Question 8: Case Type
        'value': '12',              # Question 12: Value £
        'customer_name': '4',       # Question 4: Customer Name
        'date_paid': '13'           # Question 13: Date Paid
    }
    
    NAME_MAPPINGS = {
        'mike': 'Michael',
        'michael': 'Michael',
        'steven': 'Steven',
        'steve': 'Steven',
        'dan': 'Daniel',
        'daniel': 'Daniel'
    }
    
    VALID_BUSINESS_TYPES = [
        'Residential Mortgage (Including BTL)',
        'Personal Insurance (Including GI)',
        'Product Transfer'
    ]
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "APIKEY": api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the JotForm API"""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request failed: {e}")
            return None
    
    def clean_advisor_name(self, name):
        """Clean and standardize advisor names"""
        if not name or name == "No Answer":
            return None
        
        name_lower = name.lower().strip()
        for key, standard_name in self.NAME_MAPPINGS.items():
            if key in name_lower:
                return standard_name
        
        return name.title().strip()
    
    def parse_date(self, date_string):
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
            return None
        except Exception as e:
            print(f"Error parsing date '{date_string}': {e}")
            return None
    
    def get_form_submissions_with_mapping(self, form_id, field_map, limit=1000):
        """Get form submissions using exact field mappings"""
        print(f"Fetching submissions for form {form_id}...")
        
        endpoint = f"/form/{form_id}/submissions"
        params = {"limit": limit}
        response = self._make_request(endpoint, params)
        
        if not response:
            return []
        
        submissions = response.get("content", [])
        print(f"Retrieved {len(submissions)} raw submissions")
        
        parsed_submissions = []
        
        for submission in submissions:
            parsed_data = {
                "submission_id": submission.get("id"),
                "created_at": submission.get("created_at"),
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
    
    def test_process_submissions(self):
        """Test processing submissions with detailed logging"""
        print("\n" + "="*60)
        print("🔄 TESTING SUBMISSION PROCESSING")
        print("="*60)
        
        submissions_data = self.get_form_submissions_with_mapping(
            self.SUBMISSION_FORM_ID, 
            self.SUBMISSION_FIELD_MAP
        )
        
        if not submissions_data:
            print("❌ No submissions data retrieved")
            return []
        
        print(f"\n📊 Processing {len(submissions_data)} submissions...")
        processed_submissions = []
        
        for i, submission in enumerate(submissions_data):
            print(f"\n📋 PROCESSING SUBMISSION {i+1}:")
            print(f"  ID: {submission.get('submission_id')}")
            print(f"  Status: {submission.get('status')}")
            
            try:
                data = submission.get("mapped_data", {})
                print(f"  Raw mapped data: {data}")
                
                # Extract and clean data
                advisor_name = self.clean_advisor_name(data.get("advisor_name", ""))
                business_type = str(data.get("business_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
                print(f"  Cleaned advisor_name: '{advisor_name}'")
                print(f"  Business type: '{business_type}'")
                print(f"  Customer: '{customer_name}'")
                
                # Parse numeric fields
                try:
                    proc_raw = data.get("expected_proc", "")
                    expected_proc = float(str(proc_raw).replace('£', '').replace(',', '') or 0)
                    print(f"  Expected proc: {proc_raw} -> {expected_proc}")
                except (ValueError, TypeError) as e:
                    expected_proc = 0
                    print(f"  Expected proc error: {e}")
                    
                try:
                    fee_raw = data.get("expected_fee", "")
                    expected_fee = float(str(fee_raw).replace('£', '').replace(',', '') or 0)
                    print(f"  Expected fee: {fee_raw} -> {expected_fee}")
                except (ValueError, TypeError) as e:
                    expected_fee = 0
                    print(f"  Expected fee error: {e}")
                
                # Parse date
                date_raw = data.get("submission_date", "")
                submission_date = self.parse_date(date_raw)
                print(f"  Date: {date_raw} -> {submission_date}")
                
                if not submission_date:
                    submission_date = self.parse_date(submission.get("created_at", ""))
                    print(f"  Fallback date: {submission_date}")
                
                # Handle referrals
                referral_to = None
                original_business_type = business_type
                if business_type and ('referral to' in business_type.lower() or business_type.lower().startswith('referral')):
                    if 'to' in business_type.lower():
                        referral_to = business_type.lower().split('to')[-1].strip().title()
                    else:
                        referral_to = business_type.replace('Referral', '').strip()
                    business_type = 'Referral'
                    print(f"  Referral detected: '{original_business_type}' -> '{business_type}', referral_to: '{referral_to}'")
                
                # Validation checks
                print(f"\n  🔍 VALIDATION CHECKS:")
                print(f"    Has advisor name: {bool(advisor_name)}")
                print(f"    Has business type: {bool(business_type)}")
                print(f"    Business type valid: {business_type in self.VALID_BUSINESS_TYPES}")
                print(f"    Is referral: {business_type == 'Referral'}")
                
                valid = bool(advisor_name) and (business_type in self.VALID_BUSINESS_TYPES or business_type == 'Referral')
                print(f"    ✅ WOULD BE PROCESSED: {valid}")
                
                if valid:
                    processed_data = {
                        'advisor_name': advisor_name,
                        'business_type': business_type,
                        'submission_date': submission_date or datetime.now().date(),
                        'customer_name': customer_name,
                        'expected_proc': expected_proc,
                        'expected_fee': expected_fee,
                        'referral_to': referral_to,
                        'jotform_id': submission.get("submission_id")
                    }
                    processed_submissions.append(processed_data)
                    print(f"    ✅ ADDED TO PROCESSED LIST")
                    print(f"    Final data: {processed_data}")
                else:
                    print(f"    ❌ REJECTED - Reasons:")
                    if not advisor_name:
                        print(f"      - No advisor name")
                    if not business_type:
                        print(f"      - No business type")
                    elif business_type not in self.VALID_BUSINESS_TYPES and business_type != 'Referral':
                        print(f"      - Invalid business type: '{business_type}'")
                        print(f"      - Valid types: {self.VALID_BUSINESS_TYPES}")
                    
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📈 FINAL RESULTS:")
        print(f"  Raw submissions: {len(submissions_data)}")
        print(f"  Processed submissions: {len(processed_submissions)}")
        print(f"  Success rate: {len(processed_submissions)/len(submissions_data)*100:.1f}%")
        
        return processed_submissions
    
    def test_process_paid_cases(self):
        """Test processing paid cases with detailed logging"""
        print("\n" + "="*60)
        print("💰 TESTING PAID CASES PROCESSING")
        print("="*60)
        
        paid_data = self.get_form_submissions_with_mapping(
            self.PAID_FORM_ID, 
            self.PAID_FIELD_MAP
        )
        
        if not paid_data:
            print("❌ No paid cases data retrieved")
            return []
        
        print(f"\n📊 Processing {len(paid_data)} paid cases...")
        processed_cases = []
        
        for i, case in enumerate(paid_data):
            print(f"\n💰 PROCESSING PAID CASE {i+1}:")
            print(f"  ID: {case.get('submission_id')}")
            
            try:
                data = case.get("mapped_data", {})
                print(f"  Raw mapped data: {data}")
                
                advisor_name = self.clean_advisor_name(data.get("advisor_name", ""))
                case_type = str(data.get("case_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
                print(f"  Cleaned advisor_name: '{advisor_name}'")
                print(f"  Case type: '{case_type}'")
                print(f"  Customer: '{customer_name}'")
                
                # Parse value
                try:
                    value_raw = data.get("value", "")
                    value = float(str(value_raw).replace('£', '').replace(',', '') or 0)
                    print(f"  Value: {value_raw} -> {value}")
                except (ValueError, TypeError) as e:
                    value = 0
                    print(f"  Value error: {e}")
                
                # Parse date
                date_raw = data.get("date_paid", "")
                date_paid = self.parse_date(date_raw)
                print(f"  Date paid: {date_raw} -> {date_paid}")
                
                if not date_paid:
                    date_paid = self.parse_date(case.get("created_at", ""))
                    print(f"  Fallback date: {date_paid}")
                
                # Validation
                print(f"\n  🔍 VALIDATION CHECKS:")
                print(f"    Has advisor name: {bool(advisor_name)}")
                print(f"    Has case type: {bool(case_type)}")
                print(f"    Has value > 0: {value > 0}")
                
                valid = bool(advisor_name) and bool(case_type) and value > 0
                print(f"    ✅ WOULD BE PROCESSED: {valid}")
                
                if valid:
                    processed_data = {
                        'advisor_name': advisor_name,
                        'case_type': case_type,
                        'value': value,
                        'date_paid': date_paid or datetime.now().date(),
                        'jotform_id': case.get("submission_id")
                    }
                    processed_cases.append(processed_data)
                    print(f"    ✅ ADDED TO PROCESSED LIST")
                    print(f"    Final data: {processed_data}")
                else:
                    print(f"    ❌ REJECTED - Reasons:")
                    if not advisor_name:
                        print(f"      - No advisor name")
                    if not case_type:
                        print(f"      - No case type")
                    if value <= 0:
                        print(f"      - Value is 0 or invalid")
                        
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📈 FINAL RESULTS:")
        print(f"  Raw paid cases: {len(paid_data)}")
        print(f"  Processed paid cases: {len(processed_cases)}")
        print(f"  Success rate: {len(processed_cases)/len(paid_data)*100:.1f}%")
        
        return processed_cases

def main():
    """Run the full sync test"""
    API_KEY = "b78b083ca0a78392acf8de69666a3577"
    
    print("🧪 FULL SYNC PROCESS TEST")
    print("="*60)
    print("This will simulate the complete sync process with detailed logging")
    
    manager = TestDataManager(API_KEY)
    
    # Test submissions
    submissions = manager.test_process_submissions()
    
    # Test paid cases  
    paid_cases = manager.test_process_paid_cases()
    
    print("\n" + "="*60)
    print("🏁 COMPLETE TEST SUMMARY")
    print("="*60)
    print(f"Submissions that would be inserted: {len(submissions)}")
    print(f"Paid cases that would be inserted: {len(paid_cases)}")
    
    if submissions:
        print(f"\n📝 SUBMISSIONS READY FOR DB:")
        for i, sub in enumerate(submissions, 1):
            print(f"  {i}. {sub['advisor_name']} - {sub['business_type']} - {sub['customer_name']}")
            
    if paid_cases:
        print(f"\n💰 PAID CASES READY FOR DB:")
        for i, case in enumerate(paid_cases, 1):
            print(f"  {i}. {case['advisor_name']} - {case['case_type']} - £{case['value']}")
    
    if not submissions and not paid_cases:
        print(f"\n❌ NO DATA WOULD BE INSERTED")
        print(f"Check the validation failures above to see why.")

if __name__ == "__main__":
    main()