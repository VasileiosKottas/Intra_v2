#!/usr/bin/env python3
"""
Test script to check what's actually in JotForm field 6 (who_referred)
This will help us understand the data structure

Usage:
    python test_jotform_data.py
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.jotform import JotFormService
from app.config import config_manager

def test_jotform_field_6():
    """Test what's in JotForm field 6 for paid cases"""
    
    print("🔍 Testing JotForm field 6 data...")
    
    # Create app context
    app = create_app('development')
    
    with app.app_context():
        try:
            # Test with Windsor company
            company = 'windsor'
            print(f"📋 Testing company: {company}")
            
            # Create JotForm service
            jotform_service = JotFormService(company)
            
            # Get raw form data (before processing)
            print("🔄 Fetching raw paid cases data from JotForm...")
            
            # Update field map to include field 6
            test_field_map = {
                'advisor_name': '5',
                'who_referred': '9',  # This is what we want to test
                'case_type': '8',
                'value': '12',
                'customer_name': '4',
                'date_paid': '13'
            }
            
            # Get submissions with our test mapping
            raw_data = jotform_service.get_form_submissions_with_mapping(
                jotform_service.paid_form_id,
                test_field_map
            )
            
            if not raw_data:
                print("❌ No data retrieved from JotForm")
                return
            
            print(f"📥 Retrieved {len(raw_data)} records")
            
            # Analyze first 10 records
            print("\n📊 Analyzing field 6 (who_referred) data:")
            print("-" * 60)
            
            field_6_values = []
            
            for i, record in enumerate(raw_data[:10]):  # First 10 records
                data = record.get("mapped_data", {})
                advisor_name = data.get("advisor_name", "Unknown")
                customer_name = data.get("customer_name", "Unknown")
                who_referred = data.get("who_referred", "")
                
                print(f"Record {i+1}:")
                print(f"  Advisor: {advisor_name}")
                print(f"  Customer: {customer_name}")
                print(f"  Who Referred (Field 6): '{who_referred}'")
                print(f"  Type: {type(who_referred)}")
                print()
                
                field_6_values.append(who_referred)
            
            # Summary
            print("\n📈 Summary of Field 6 values:")
            empty_count = sum(1 for v in field_6_values if not str(v).strip())
            filled_count = len(field_6_values) - empty_count
            
            print(f"  Total checked: {len(field_6_values)}")
            print(f"  Empty/None: {empty_count}")
            print(f"  With data: {filled_count}")
            
            if filled_count > 0:
                print("\n📋 Non-empty values found:")
                for v in field_6_values:
                    if str(v).strip():
                        print(f"  - '{v}'")
            
            # Test a larger sample
            print(f"\n🔍 Checking all {len(raw_data)} records for field 6 data...")
            all_field_6_values = []
            
            for record in raw_data:
                data = record.get("mapped_data", {})
                who_referred = str(data.get("who_referred", "")).strip()
                if who_referred:
                    all_field_6_values.append(who_referred)
            
            print(f"📊 Total records with who_referred data: {len(all_field_6_values)} out of {len(raw_data)}")
            
            if all_field_6_values:
                print("\n📋 All unique who_referred values:")
                unique_values = list(set(all_field_6_values))
                for value in unique_values:
                    print(f"  - '{value}'")
            else:
                print("❌ No who_referred data found in any records!")
                print("💡 This could mean:")
                print("   1. Field 6 is not being filled in the JotForm")
                print("   2. Field 6 mapping is incorrect")
                print("   3. Field 6 might have a different question ID")
                
        except Exception as e:
            print(f"❌ Error testing JotForm data: {e}")
            raise

if __name__ == '__main__':
    try:
        test_jotform_field_6()
    except KeyboardInterrupt:
        print("\n⛔ Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)