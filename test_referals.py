# analyze_referrals_sqlite.py
"""
SQLite-compatible script to analyze referral data in submissions table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import SalesDashboardApp
from app.models import db
from sqlalchemy import text
from collections import Counter

def analyze_referrals():
    """Analyze all referral data in the submissions table"""
    app_instance = SalesDashboardApp()
    
    with app_instance.app.app_context():
        print("📊 Analyzing referral data in submissions table...")
        
        try:
            with db.engine.connect() as connection:
                # First, let's check what columns exist
                print("🔍 Checking table structure...")
                table_info = connection.execute(text("PRAGMA table_info(submissions)")).fetchall()
                columns = [col[1] for col in table_info]
                print(f"Available columns: {columns}")
                
                has_original_field = 'original_business_type' in columns
                print(f"Has original_business_type field: {has_original_field}")
                
                # Get all referral-related submissions (SQLite compatible)
                if has_original_field:
                    query = """
                        SELECT 
                            business_type,
                            referral_to,
                            original_business_type,
                            advisor_name,
                            customer_name,
                            submission_date,
                            company
                        FROM submissions 
                        WHERE LOWER(business_type) LIKE '%referral%' 
                        OR referral_to IS NOT NULL
                        ORDER BY submission_date DESC
                    """
                else:
                    query = """
                        SELECT 
                            business_type,
                            referral_to,
                            advisor_name,
                            customer_name,
                            submission_date,
                            company
                        FROM submissions 
                        WHERE LOWER(business_type) LIKE '%referral%' 
                        OR referral_to IS NOT NULL
                        ORDER BY submission_date DESC
                    """
                
                result = connection.execute(text(query))
                referrals = result.fetchall()
                
                if not referrals:
                    print("❌ No referral data found in submissions table")
                    
                    # Let's check what data exists
                    total_count = connection.execute(text("SELECT COUNT(*) FROM submissions")).fetchone()[0]
                    print(f"Total submissions in table: {total_count}")
                    
                    # Check for any business types
                    business_types = connection.execute(text("""
                        SELECT DISTINCT business_type, COUNT(*) as count
                        FROM submissions 
                        WHERE business_type IS NOT NULL
                        GROUP BY business_type
                        ORDER BY count DESC
                    """)).fetchall()
                    
                    print("All business types found:")
                    for bt in business_types:
                        print(f"  '{bt[0]}': {bt[1]} records")
                    
                    return
                
                print(f"✅ Found {len(referrals)} referral-related submissions")
                print("\n" + "="*80)
                
                # Analyze business types
                print("📈 BUSINESS TYPE ANALYSIS:")
                business_types = []
                for r in referrals:
                    if r.business_type:
                        business_types.append(r.business_type)
                
                business_type_counts = Counter(business_types)
                
                for bt, count in business_type_counts.most_common():
                    print(f"  '{bt}': {count} records")
                
                print("\n" + "-"*50)
                
                # Analyze referral_to values
                print("👤 REFERRAL TO ANALYSIS:")
                referral_to_values = []
                for r in referrals:
                    if r.referral_to and r.referral_to.strip():
                        referral_to_values.append(r.referral_to)
                
                referral_to_counts = Counter(referral_to_values)
                
                print(f"Found {len(referral_to_counts)} unique referral_to values:")
                for rt, count in referral_to_counts.most_common():
                    print(f"  '{rt}': {count} records")
                
                print("\n" + "-"*50)
                
                # Analyze original_business_type if it exists
                if has_original_field:
                    print("📋 ORIGINAL BUSINESS TYPE ANALYSIS:")
                    original_types = []
                    
                    for r in referrals:
                        if hasattr(r, 'original_business_type') and r.original_business_type:
                            original_types.append(r.original_business_type)
                    
                    if original_types:
                        original_type_counts = Counter(original_types)
                        
                        for ot, count in original_type_counts.most_common():
                            print(f"  '{ot}': {count} records")
                    else:
                        print("  No original_business_type data populated yet")
                else:
                    print("⚠️  No 'original_business_type' field found (migration not run)")
                
                print("\n" + "-"*50)
                
                # Search for conveyancing/survey patterns - prioritize original_business_type
                print("🔍 SEARCHING FOR CONVEYANCING/SURVEY PATTERNS:")
                
                conveyancing_patterns = []
                survey_patterns = []
                
                for r in referrals:
                    # Prioritize original_business_type, then fall back to other fields
                    search_fields = []
                    
                    if has_original_field and hasattr(r, 'original_business_type') and r.original_business_type:
                        # Primary source: original_business_type (the real JotForm data)
                        search_fields.append(r.original_business_type)
                    
                    # Secondary sources: referral_to and business_type
                    if r.referral_to:
                        search_fields.append(r.referral_to)
                    if r.business_type:
                        search_fields.append(r.business_type)
                    
                    all_text = ' '.join(search_fields).lower()
                    
                    if any(keyword in all_text for keyword in ['conveyancing', 'conveyance', 'conveyanc']):
                        conv_data = {
                            'business_type': r.business_type,
                            'referral_to': r.referral_to,
                            'advisor': r.advisor_name,
                            'date': r.submission_date
                        }
                        if has_original_field and hasattr(r, 'original_business_type'):
                            conv_data['original_business_type'] = r.original_business_type
                        conveyancing_patterns.append(conv_data)
                    
                    if any(keyword in all_text for keyword in ['survey', 'surveyor', 'surveying']):
                        surv_data = {
                            'business_type': r.business_type,
                            'referral_to': r.referral_to,
                            'advisor': r.advisor_name,
                            'date': r.submission_date
                        }
                        if has_original_field and hasattr(r, 'original_business_type'):
                            surv_data['original_business_type'] = r.original_business_type
                        survey_patterns.append(surv_data)
                
                print(f"🏠 Conveyancing patterns found: {len(conveyancing_patterns)}")
                for i, conv in enumerate(conveyancing_patterns[:10], 1):
                    orig = conv.get('original_business_type', 'N/A')
                    print(f"  {i}. {conv['business_type']} | {conv['referral_to']} | {orig} | {conv['advisor']} | {conv['date']}")
                
                print(f"📏 Survey patterns found: {len(survey_patterns)}")
                for i, surv in enumerate(survey_patterns[:10], 1):
                    orig = surv.get('original_business_type', 'N/A')
                    print(f"  {i}. {surv['business_type']} | {surv['referral_to']} | {orig} | {surv['advisor']} | {surv['date']}")
                
                print("\n" + "-"*50)
                
                # Show recent samples
                print("📅 RECENT REFERRAL SAMPLES (Last 20):")
                if has_original_field:
                    print("Date       | Advisor        | Business Type      | Referral To        | Original Type")
                    print("-" * 95)
                else:
                    print("Date       | Advisor        | Business Type      | Referral To")
                    print("-" * 75)
                
                for r in referrals[:20]:
                    # Handle date formatting - might be string or datetime
                    if r.submission_date:
                        if hasattr(r.submission_date, 'strftime'):
                            date_str = r.submission_date.strftime('%Y-%m-%d')
                        else:
                            date_str = str(r.submission_date)[:10]  # Take first 10 chars if it's a string
                    else:
                        date_str = 'N/A'
                        
                    advisor = (r.advisor_name or '')[:15].ljust(15)
                    business = (r.business_type or '')[:18].ljust(18)
                    referral = (r.referral_to or '')[:18].ljust(18)
                    
                    if has_original_field and hasattr(r, 'original_business_type'):
                        original = (r.original_business_type or '')[:15]
                        print(f"{date_str} | {advisor} | {business} | {referral} | {original}")
                    else:
                        print(f"{date_str} | {advisor} | {business} | {referral}")
                
                print("\n" + "="*80)
                
                # Summary and recommendations
                print("💡 ANALYSIS SUMMARY:")
                print(f"   Total referrals: {len(referrals)}")
                print(f"   Unique business types: {len(business_type_counts)}")
                print(f"   Unique referral_to values: {len(referral_to_counts)}")
                print(f"   Conveyancing mentions: {len(conveyancing_patterns)}")
                print(f"   Survey mentions: {len(survey_patterns)}")
                
                if len(conveyancing_patterns) == 0 and len(survey_patterns) == 0:
                    print("\n⚠️  NO CONVEYANCING OR SURVEY REFERRALS FOUND")
                    print("   This suggests:")
                    print("   1. These referral types might not exist in your current data")
                    print("   2. They might be labeled differently than expected")
                    print("   3. The 'Other Referrals' category logic may need adjustment")
                    print("\n💭 RECOMMENDATIONS:")
                    print("   - Review the actual referral_to values above")
                    print("   - Consider what should count as 'Other Referrals' in your YTD reports")
                    print("   - Update the categorization logic based on your actual data patterns")
                
                # Suggest what could be "Other Referrals"
                if referral_to_counts:
                    print("\n🎯 SUGGESTED 'OTHER REFERRALS' CATEGORIES:")
                    print("   Based on your actual data, consider these for 'Other Referrals':")
                    non_insurance_referrals = []
                    for rt, count in referral_to_counts.most_common():
                        rt_lower = rt.lower()
                        if not any(keyword in rt_lower for keyword in ['insurance', 'protection']):
                            non_insurance_referrals.append((rt, count))
                    
                    for rt, count in non_insurance_referrals[:10]:
                        print(f"     - '{rt}' ({count} records)")
                
                return {
                    'total_referrals': len(referrals),
                    'business_types': dict(business_type_counts),
                    'referral_to_values': dict(referral_to_counts),
                    'conveyancing_found': len(conveyancing_patterns),
                    'survey_found': len(survey_patterns),
                    'has_original_field': has_original_field
                }
                
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """Main analysis function"""
    analyze_referrals()

if __name__ == '__main__':
    main()