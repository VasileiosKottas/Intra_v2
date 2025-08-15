#!/usr/bin/env python3
"""
Debug JotForm Sync - Detailed analysis of what's happening during sync
"""

import requests
import json
from datetime import datetime

def debug_jotform_sync():
    """Debug the JotForm sync process step by step"""
    
    API_KEY = "b78b083ca0a78392acf8de69666a3577"
    BASE_URL = "https://eu-api.jotform.com"
    SUBMISSION_FORM_ID = "250232251408041"  # Submission Form
    PAID_FORM_ID = "251406545360048"        # Pay and Commission Tracking
    
    headers = {
        "APIKEY": API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    print("🔍 DEBUGGING JOTFORM SYNC PROCESS")
    print("=" * 60)
    
    # Step 1: Test Submissions Form
    print(f"\n1️⃣ ANALYZING SUBMISSIONS FORM (ID: {SUBMISSION_FORM_ID})")
    print("-" * 60)
    
    # Get form questions first
    try:
        q_response = requests.get(f"{BASE_URL}/form/{SUBMISSION_FORM_ID}/questions", headers=headers)
        if q_response.status_code == 200:
            questions = q_response.json().get('content', {})
            print(f"✅ Found {len(questions)} questions in submissions form")
            
            # Show all questions
            print("\n📝 ALL QUESTIONS:")
            for q_id, q_data in questions.items():
                q_text = q_data.get('text', 'No text')
                q_type = q_data.get('type', 'Unknown')
                print(f"  Q{q_id}: {q_text} [{q_type}]")
        else:
            print(f"❌ Error getting questions: {q_response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Get submissions
    try:
        s_response = requests.get(f"{BASE_URL}/form/{SUBMISSION_FORM_ID}/submissions", 
                                headers=headers, params={"limit": 3})
        if s_response.status_code == 200:
            submissions_data = s_response.json()
            submissions = submissions_data.get('content', [])
            print(f"\n✅ Found {len(submissions)} submissions")
            
            if submissions:
                print(f"\n🔍 DETAILED ANALYSIS OF FIRST SUBMISSION:")
                first_sub = submissions[0]
                print(f"  Submission ID: {first_sub.get('id')}")
                print(f"  Created: {first_sub.get('created_at')}")
                print(f"  Status: {first_sub.get('status')}")
                
                answers = first_sub.get('answers', {})
                print(f"  Total Answers: {len(answers)}")
                
                print(f"\n  📋 ALL ANSWERS:")
                for answer_id, answer_data in answers.items():
                    if isinstance(answer_data, dict):
                        answer_value = answer_data.get('answer', 'No Answer')
                        answer_type = answer_data.get('type', 'Unknown')
                        print(f"    A{answer_id}: {answer_value} [Type: {answer_type}]")
                    else:
                        print(f"    A{answer_id}: {answer_data}")
                
                # Test our field mapping
                print(f"\n  🎯 TESTING FIELD MAPPING:")
                field_map = {
                    'advisor_name': '5',
                    'business_type': '3', 
                    'submission_date': '6',
                    'customer_name': '7',
                    'expected_proc': '12',
                    'expected_fee': '13'
                }
                
                for field_name, question_id in field_map.items():
                    if question_id in answers:
                        answer_data = answers[question_id]
                        if isinstance(answer_data, dict):
                            value = answer_data.get('answer', 'No Answer')
                        else:
                            value = str(answer_data)
                        print(f"    ✅ {field_name} (Q{question_id}): {value}")
                    else:
                        print(f"    ❌ {field_name} (Q{question_id}): NOT FOUND")
                
        else:
            print(f"❌ Error getting submissions: {s_response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Step 2: Test Paid Form
    print(f"\n\n2️⃣ ANALYZING PAID FORM (ID: {PAID_FORM_ID})")
    print("-" * 60)
    
    # Get paid form questions
    try:
        q_response = requests.get(f"{BASE_URL}/form/{PAID_FORM_ID}/questions", headers=headers)
        if q_response.status_code == 200:
            questions = q_response.json().get('content', {})
            print(f"✅ Found {len(questions)} questions in paid form")
            
            # Show key questions
            print(f"\n📝 ALL QUESTIONS:")
            for q_id, q_data in questions.items():
                q_text = q_data.get('text', 'No text')
                q_type = q_data.get('type', 'Unknown')
                print(f"  Q{q_id}: {q_text} [{q_type}]")
        else:
            print(f"❌ Error getting questions: {q_response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Get paid submissions
    try:
        p_response = requests.get(f"{BASE_URL}/form/{PAID_FORM_ID}/submissions", 
                                headers=headers, params={"limit": 3})
        if p_response.status_code == 200:
            paid_data = p_response.json()
            paid_submissions = paid_data.get('content', [])
            print(f"\n✅ Found {len(paid_submissions)} paid submissions")
            
            if paid_submissions:
                print(f"\n🔍 DETAILED ANALYSIS OF FIRST PAID SUBMISSION:")
                first_paid = paid_submissions[0]
                print(f"  Submission ID: {first_paid.get('id')}")
                print(f"  Created: {first_paid.get('created_at')}")
                
                answers = first_paid.get('answers', {})
                print(f"  Total Answers: {len(answers)}")
                
                print(f"\n  📋 ALL ANSWERS:")
                for answer_id, answer_data in answers.items():
                    if isinstance(answer_data, dict):
                        answer_value = answer_data.get('answer', 'No Answer')
                        answer_type = answer_data.get('type', 'Unknown')
                        print(f"    A{answer_id}: {answer_value} [Type: {answer_type}]")
                    else:
                        print(f"    A{answer_id}: {answer_data}")
                
                # Test paid field mapping
                print(f"\n  🎯 TESTING PAID FIELD MAPPING:")
                paid_field_map = {
                    'advisor_name': '5',
                    'case_type': '8',
                    'value': '1',
                    'customer_name': '4',
                    'date_paid': '6'
                }
                
                for field_name, question_id in paid_field_map.items():
                    if question_id in answers:
                        answer_data = answers[question_id]
                        if isinstance(answer_data, dict):
                            value = answer_data.get('answer', 'No Answer')
                        else:
                            value = str(answer_data)
                        print(f"    ✅ {field_name} (Q{question_id}): {value}")
                    else:
                        print(f"    ❌ {field_name} (Q{question_id}): NOT FOUND")
        else:
            print(f"❌ Error getting paid submissions: {p_response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Step 3: Simulate Processing
    print(f"\n\n3️⃣ SIMULATING DATA PROCESSING")
    print("-" * 60)
    
    # Test submission processing logic
    if 'submissions' in locals() and submissions:
        print("🔄 Testing submission processing...")
        
        test_submission = submissions[0]
        answers = test_submission.get('answers', {})
        
        # Extract data using our mapping
        advisor_name = None
        business_type = None
        
        if '5' in answers:  # Advisor name
            advisor_data = answers['5']
            if isinstance(advisor_data, dict):
                advisor_name = advisor_data.get('answer', '')
            else:
                advisor_name = str(advisor_data)
            print(f"  Raw advisor name: '{advisor_name}'")
        
        if '3' in answers:  # Business type
            business_data = answers['3']
            if isinstance(business_data, dict):
                business_type = business_data.get('answer', '')
            else:
                business_type = str(business_data)
            print(f"  Raw business type: '{business_type}'")
        
        # Test validation
        valid_business_types = [
            'Residential Mortgage (Including BTL)',
            'Personal Insurance (Including GI)',
            'Product Transfer'
        ]
        
        print(f"\n  🧪 VALIDATION TESTS:")
        print(f"    Advisor name exists: {bool(advisor_name)}")
        print(f"    Business type exists: {bool(business_type)}")
        print(f"    Business type valid: {business_type in valid_business_types}")
        print(f"    Is referral: {'referral' in business_type.lower() if business_type else False}")
        
        would_process = bool(advisor_name) and (business_type in valid_business_types or 'referral' in business_type.lower())
        print(f"    ✅ Would be processed: {would_process}")
        
        if not would_process:
            print(f"    ❌ REASON NOT PROCESSED:")
            if not advisor_name:
                print(f"      - No advisor name found")
            if business_type and business_type not in valid_business_types and 'referral' not in business_type.lower():
                print(f"      - Business type '{business_type}' not in valid list")
    
    print(f"\n" + "=" * 60)
    print("🏁 DEBUG COMPLETE")
    print("Check the output above to see where the data processing is failing.")

if __name__ == "__main__":
    debug_jotform_sync()
