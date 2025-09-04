#!/usr/bin/env python3
"""
Tonight's ALTOS Data Capture Runner
Simple script to run tonight and capture the data structure
"""

import os
import sys
from datetime import datetime

print("🌙 ALTOS Data Capture - Tonight's Mission")
print("=" * 50)
print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check if we're in the right time window
current_hour = datetime.now().hour
if 0 <= current_hour < 6:
    print("✅ Perfect! You're in the API window (00:00-06:00)")
    run_now = True
else:
    print(f"⏰ Current time: {current_hour}:xx")
    print("⚠️  API is only available 00:00-06:00")
    print()
    response = input("Do you want to run the capture script anyway to test structure? (y/n): ")
    run_now = response.lower().startswith('y')

if run_now:
    print("\n🚀 Starting ALTOS data capture...")
    print("This will:")
    print("  • Test different date ranges")
    print("  • Capture successful API responses")
    print("  • Analyze data structure")
    print("  • Create integration summary")
    print()
    
    try:
        # Import and run the capture script
        if os.path.exists('altos_data_capture.py'):
            exec(open('altos_data_capture.py', encoding="utf-8").read())
        else:
            print("❌ altos_data_capture.py not found!")
            print("Please make sure the data capture script is in the current directory")
            
    except Exception as e:
        print(f"❌ Error running capture: {e}")
        import traceback
        traceback.print_exc()

else:
    print("\n⏹️  Capture cancelled")
    print("\n📋 TO RUN TONIGHT:")
    print("1. Set an alarm for 3:00 AM")
    print("2. Run: python tonight_runner.py")
    print("3. Let it capture the data structure")
    print("4. Review results in the morning")
    print()
    print("📁 Files will be saved in: ./altos_data_capture/")

print("\n🎯 After capture completes:")
print("• Check the INTEGRATION_SUMMARY file")
print("• Review sample data structure")
print("• Use the integration instructions")
print("• Add to your existing sync system")

input("\nPress Enter to exit...")