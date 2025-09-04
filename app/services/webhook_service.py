"""
Webhook processing service for JotForm data
"""

from datetime import datetime
from typing import Tuple
from app.models import db
from app.models.advisor import Advisor
from app.models.submission import Submission
from app.models.paid_case import PaidCase
from app.config import config_manager

class WebhookService:
    """Service for processing JotForm webhooks"""
    
    def __init__(self):
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
            'income_type': '6'
        }
    
    def process_submission_webhook(self, webhook_data: dict) -> Tuple[bool, str]:
        """Process a submission webhook from JotForm"""
        try:
            # Extract form ID to determine company
            form_id = str(webhook_data.get('formID', ''))
            submission_id = webhook_data.get('submissionID', '')
            
            # Determine company based on form configuration
            company = self._determine_company_from_form(form_id)
            if not company:
                return False, f"Unknown form ID: {form_id}"
            
            # Check if already processed
            existing = Submission.query.filter_by(jotform_id=submission_id).first()
            if existing:
                return True, f"Submission {submission_id} already processed"
            
            # Extract and process submission data
            answers = webhook_data.get('rawRequest', {}).get('answers', {})
            if not answers:
                # Try alternative structure
                answers = webhook_data.get('answers', {})
            
            processed_data = self._process_submission_data(answers, company, submission_id)
            if not processed_data:
                return False, "Failed to process submission data"
            
            # Create submission record
            advisor = Advisor.query.filter_by(full_name=processed_data['advisor_name']).first()
            
            submission = Submission(
                advisor_name=processed_data['advisor_name'],
                advisor_id=advisor.id if advisor else None,
                business_type=processed_data['business_type'],
                submission_date=processed_data['submission_date'],
                customer_name=processed_data['customer_name'],
                expected_proc=processed_data['expected_proc'],
                expected_fee=processed_data['expected_fee'],
                referral_to=processed_data.get('referral_to'),
                company=company,
                jotform_id=submission_id
            )
            
            submission.save()
            
            print(f"✅ Webhook: Added submission {submission_id} for {company}")
            return True, f"Successfully processed submission {submission_id}"
            
        except Exception as e:
            print(f"❌ Webhook error processing submission: {str(e)}")
            return False, f"Error processing submission: {str(e)}"
    
    def process_paid_case_webhook(self, webhook_data: dict) -> Tuple[bool, str]:
        """Process a paid case webhook from JotForm"""
        try:
            form_id = str(webhook_data.get('formID', ''))
            submission_id = webhook_data.get('submissionID', '')
            
            company = self._determine_company_from_form(form_id)
            if not company:
                return False, f"Unknown form ID: {form_id}"
            
            # Check if already processed
            existing = PaidCase.query.filter_by(jotform_id=submission_id).first()
            if existing:
                # Update existing record if needed
                answers = webhook_data.get('rawRequest', {}).get('answers', {})
                if not answers:
                    answers = webhook_data.get('answers', {})
                
                processed_data = self._process_paid_case_data(answers, company, submission_id)
                if processed_data and processed_data.get('who_referred') != existing.who_referred:
                    existing.who_referred = processed_data.get('who_referred')
                    db.session.commit()
                    return True, f"Updated paid case {submission_id}"
                
                return True, f"Paid case {submission_id} already processed"
            
            # Extract and process paid case data
            answers = webhook_data.get('rawRequest', {}).get('answers', {})
            if not answers:
                answers = webhook_data.get('answers', {})
            
            processed_data = self._process_paid_case_data(answers, company, submission_id)
            if not processed_data:
                return False, "Failed to process paid case data"
            
            # Create paid case record
            advisor = Advisor.query.filter_by(full_name=processed_data['advisor_name']).first()
            
            paid_case = PaidCase(
                advisor_name=processed_data['advisor_name'],
                advisor_id=advisor.id if advisor else None,
                customer_name=processed_data['customer_name'],
                case_type=processed_data['case_type'],
                value=processed_data['value'],
                date_paid=processed_data['date_paid'],
                who_referred=processed_data.get('who_referred'),
                company=company,
                jotform_id=submission_id
            )
            
            paid_case.save()
            
            print(f"✅ Webhook: Added paid case {submission_id} for {company}")
            return True, f"Successfully processed paid case {submission_id}"
            
        except Exception as e:
            print(f"❌ Webhook error processing paid case: {str(e)}")
            return False, f"Error processing paid case: {str(e)}"
    
    def _determine_company_from_form(self, form_id: str) -> str:
        """Determine company based on form ID or other logic"""
        # You can implement company detection based on:
        # 1. Different form IDs for different companies
        # 2. A field in the form that specifies company
        # 3. Default to 'windsor' for now
        
        # Example: Different forms for different companies
        # if form_id == "250232251408041":  # Submission form
        #     return "windsor"  # or determine from form data
        # elif form_id == "251406545360048":  # Paid case form
        #     return "windsor"  # or determine from form data
        
        # For now, default to windsor but you can enhance this
        return "windsor"
    def _process_submission_data(self, answers: dict, company: str, submission_id: str) -> dict:
        """Enhanced webhook processing to capture all referrals"""
        try:
            config = config_manager.get_company_config(company)
            if not config:
                return None
            
            # Extract data
            data = {}
            for data_key, question_id in self.submission_field_map.items():
                if question_id in answers:
                    answer_value = answers[question_id].get('answer', '')
                    data[data_key] = answer_value if answer_value != 'No Answer' else ''
            
            advisor_name = config.normalize_advisor_name(data.get('advisor_name', ''))
            business_type = str(data.get('business_type', ''))
            customer_name = str(data.get('customer_name', '') or 'Unknown Customer')
            
            # Store original BEFORE any changes
            original_business_type = business_type
            
            # Process values...
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
                submission_date = datetime.now().date()
            
            # Handle referrals
            referral_to = None
            is_referral = 'referral' in business_type.lower()
            
            if is_referral:
                if 'referral to' in business_type.lower():
                    referral_to = business_type.lower().split('referral to')[-1].strip().title()
                business_type = 'Referral'
            
            # Save if valid business type OR any referral
            if not advisor_name:
                return None
                
            if not (config.is_valid_business_type(business_type) or is_referral):
                return None
            
            return {
                'advisor_name': advisor_name,
                'business_type': business_type,
                'original_business_type': original_business_type,
                'submission_date': submission_date,
                'customer_name': customer_name,
                'expected_proc': expected_proc,
                'expected_fee': expected_fee,
                'referral_to': referral_to
            }
            
        except Exception as e:
            print(f"Error processing submission data: {str(e)}")
            return None
    
    def _process_paid_case_data(self, answers: dict, company: str, submission_id: str) -> dict:
        """Process paid case data from webhook answers"""
        try:
            config = config_manager.get_company_config(company)
            if not config:
                return None
            
            # Extract data using field mappings
            data = {}
            for data_key, question_id in self.paid_field_map.items():
                if question_id in answers:
                    answer_data = answers[question_id]
                    if isinstance(answer_data, dict):
                        answer_value = answer_data.get("answer", "")
                    else:
                        answer_value = str(answer_data)
                    data[data_key] = answer_value
                else:
                    data[data_key] = ""
            
            # Process and validate data
            advisor_name = config.normalize_advisor_name(data.get("advisor_name", ""))
            case_type = str(data.get("case_type", ""))
            customer_name = str(data.get("customer_name", "") or "Unknown Customer")
            
            # Handle who_referred
            who_referred_raw = data.get("who_referred", "")
            who_referred = self._normalize_referrer_name(who_referred_raw, config)
            
            # Handle value
            try:
                value_raw = data.get("value", "")
                if value_raw and value_raw != "No Answer":
                    value_str = str(value_raw).replace('£', '').replace(',', '').strip()
                    value = float(value_str or 0)
                else:
                    value = 0
            except (ValueError, TypeError):
                value = 0
            
            # Handle date
            date_paid = self._parse_date(data.get("date_paid", ""))
            if not date_paid:
                date_paid = datetime.now().date()
            
            # Validate
            if not advisor_name or not config.is_valid_paid_case_type(case_type) or value == 0:
                return None
            
            return {
                'advisor_name': advisor_name,
                'case_type': case_type,
                'value': value,
                'customer_name': customer_name,
                'date_paid': date_paid,
                'who_referred': who_referred
            }
            
        except Exception as e:
            print(f"Error processing paid case data: {str(e)}")
            return None
    
    def _parse_date(self, date_string) -> datetime.date:
        """Parse date from various formats"""
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
        except Exception:
            return None
    
    def _normalize_referrer_name(self, who_referred_raw, config):
        """Normalize referrer name using company config"""
        if not who_referred_raw:
            return None
        
        who_referred_clean = str(who_referred_raw).strip()
        
        if not who_referred_clean or who_referred_clean.lower() in ["no answer", "none", ""]:
            return None
        
        # Use company config to normalize
        normalized_name = config.normalize_advisor_name(who_referred_clean)
        
        if normalized_name and normalized_name in config.advisor_names:
            return normalized_name
        
        return who_referred_clean