"""
JotForm API integration service
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
from app.config import config_manager

class JotFormService:
    """Service for JotForm API integration"""
    
    def __init__(self, company: str):
        self.company = company
        self.config = config_manager.get_company_config(company)
        self.api_key = config_manager.get_app_config('JOTFORM_API_KEY')
        self.base_url = config_manager.get_app_config('BASE_URL')
        self.submission_form_id = config_manager.get_app_config('SUBMISSION_FORM_ID')
        self.paid_form_id = config_manager.get_app_config('PAID_FORM_ID')
        
        self.headers = {
            "APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Field mappings
        self.submission_field_map = {
            'advisor_name': '39',
            'business_type': '3',
            'submission_date': '6',
            'customer_name': '7',
            'expected_proc': '12',
            'expected_fee': '13'
        }
        
        self.paid_field_map = {
            'advisor_name': '5',
            'who_referred': '9',
            'case_type': '8',
            'value': '12',
            'customer_name': '4',
            'date_paid': '13'
        }
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to the JotForm API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f" API request failed: {str(e)}")
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
            print(f" Error parsing date '{date_string}': {e}")
            return None
    
    def get_form_submissions_with_mapping(self, form_id: str, field_map: Dict, limit: int = 1000) -> List[Dict]:
        """Get form submissions using exact field mappings"""
        print(f" Fetching submissions for form {form_id} (Company: {self.company})...")
        
        endpoint = f"/form/{form_id}/submissions"
        params = {"limit": limit}
        response = self._make_request(endpoint, params)
        
        if not response:
            return []
        
        submissions = response.get("content", [])
        print(f" Retrieved {len(submissions)} raw submissions")
        
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
    
    def process_submissions(self) -> List[Dict]:
        """Process submissions with company-specific filtering"""
        print(f" Processing submissions from JotForm for {self.company}...")
        
        submissions_data = self.get_form_submissions_with_mapping(
            self.submission_form_id, 
            self.submission_field_map
        )
        
        if not submissions_data:
            print(" No submissions data retrieved")
            return []
        
        processed_submissions = []
        
        for submission in submissions_data:
            try:
                data = submission.get("mapped_data", {})
                
                advisor_name = self.config.normalize_advisor_name(data.get("advisor_name", ""))
                business_type = str(data.get("business_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
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
                    submission_date = self._parse_date(submission.get("created_at", ""))
                
                referral_to = None
                if business_type and ('referral to' in business_type.lower() or business_type.lower().startswith('referral')):
                    if 'to' in business_type.lower():
                        referral_to = business_type.lower().split('to')[-1].strip().title()
                    else:
                        referral_to = business_type.replace('Referral', '').strip()
                    business_type = 'Referral'
                
                # Company-specific filtering: Only process valid business types OR referrals
                if advisor_name and (self.config.is_valid_business_type(business_type) or business_type == 'Referral'):
                    processed_submissions.append({
                        'advisor_name': advisor_name,
                        'business_type': business_type,
                        'submission_date': submission_date or datetime.now().date(),
                        'customer_name': customer_name,
                        'expected_proc': expected_proc,
                        'expected_fee': expected_fee,
                        'referral_to': referral_to,
                        'company': self.company,
                        'jotform_id': submission.get("submission_id")
                    })
                    
            except Exception as e:
                print(f" Error processing submission: {e}")
                continue
        
        print(f" Successfully processed {len(processed_submissions)} valid submissions for {self.company}")
        return processed_submissions
    
    def process_paid_cases(self) -> List[Dict]:
        """Process paid cases with company-specific filtering"""
        print(f" Processing paid cases from JotForm for {self.company}...")
        
        paid_data = self.get_form_submissions_with_mapping(
            self.paid_form_id, 
            self.paid_field_map
        )
        
        if not paid_data:
            print(" No paid cases data retrieved")
            return []
        
        processed_cases = []

        for case in paid_data:
            try:
                data = case.get("mapped_data", {})
                
                advisor_name = self.config.normalize_advisor_name(data.get("advisor_name", ""))
                case_type = str(data.get("case_type", ""))
                customer_name = str(data.get("customer_name", "") or "Unknown Customer")
                
                try:
                    value_raw = data.get("value", "")
                    if value_raw and value_raw != "No Answer":
                        # Handle negative values properly
                        value_str = str(value_raw).replace('£', '').replace(',', '').strip()
                        value = float(value_str or 0)
                    else:
                        value = 0
                except (ValueError, TypeError):
                    value = 0
                
                date_paid = self._parse_date(data.get("date_paid", ""))
                if not date_paid:
                    date_paid = self._parse_date(case.get("created_at", ""))
                
                # Company-specific filtering - FIXED: Remove the value > 0 condition
                # This allows negative values (adjustments, refunds, etc.) to be included
                if (advisor_name and 
                    self.config.is_valid_paid_case_type(case_type) and 
                    value != 0):  # Only exclude zero values, allow negative values
                    processed_cases.append({
                        'advisor_name': advisor_name,
                        'case_type': case_type,
                        'value': value,
                        'customer_name': customer_name,
                        'date_paid': date_paid or datetime.now().date(),
                        'company': self.company,
                        'jotform_id': case.get("submission_id")
                    })
            except Exception as e:
                print(f" Error processing paid case: {e}")
                continue
        
        print(f" Successfully processed {len(processed_cases)} valid paid cases for {self.company}")
        return processed_cases