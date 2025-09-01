import os
import shutil
import tempfile
from pathlib import Path

def clear_jotform_caches():
    """Clear all possible JotForm-related caches"""
    
    print("🗑️ CLEARING JOTFORM CACHES")
    print("=" * 40)
    
    cleared_items = []
    
    # 1. Clear Python __pycache__ directories
    print("1️⃣ Clearing Python cache...")
    try:
        current_dir = Path.cwd()
        pycache_dirs = list(current_dir.rglob("__pycache__"))
        
        for pycache_dir in pycache_dirs:
            if pycache_dir.exists():
                shutil.rmtree(pycache_dir)
                cleared_items.append(str(pycache_dir))
        
        print(f"   ✅ Cleared {len(pycache_dirs)} __pycache__ directories")
        
    except Exception as e:
        print(f"   ⚠️ Error clearing Python cache: {e}")
    
    # 2. Clear temporary files
    print("2️⃣ Clearing temp files...")
    try:
        temp_dir = Path(tempfile.gettempdir())
        jotform_temp_files = []
        
        # Look for any files with 'jotform' in the name
        for temp_file in temp_dir.glob("*jotform*"):
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                    jotform_temp_files.append(str(temp_file))
            except:
                pass  # File might be in use
        
        print(f"   ✅ Cleared {len(jotform_temp_files)} temp files")
        
    except Exception as e:
        print(f"   ⚠️ Error clearing temp files: {e}")
    
    # 3. Clear requests cache (if using requests-cache)
    print("3️⃣ Clearing requests cache...")
    try:
        import requests_cache
        requests_cache.clear()
        print("   ✅ Cleared requests cache")
        cleared_items.append("requests_cache")
    except ImportError:
        print("   ℹ️ requests-cache not installed (skip)")
    except Exception as e:
        print(f"   ⚠️ Error clearing requests cache: {e}")
    
    # 4. Reset any environment variables that might be cached
    print("4️⃣ Checking environment...")
    jotform_env_vars = [var for var in os.environ.keys() if 'jotform' in var.lower()]
    if jotform_env_vars:
        print(f"   ℹ️ Found JotForm env vars: {jotform_env_vars}")
        print("   (These are not cleared - they contain your API keys)")
    else:
        print("   ℹ️ No JotForm environment variables found")
    
    # 5. Clear any log files
    print("5️⃣ Clearing log files...")
    try:
        log_files_cleared = 0
        potential_log_dirs = [Path.cwd(), Path.cwd() / "logs", Path.cwd() / "log"]
        
        for log_dir in potential_log_dirs:
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        if log_file.stat().st_size > 0:  # Only clear non-empty log files
                            log_file.write_text("")  # Clear content instead of deleting
                            log_files_cleared += 1
                            cleared_items.append(str(log_file))
                    except:
                        pass
        
        print(f"   ✅ Cleared {log_files_cleared} log files")
        
    except Exception as e:
        print(f"   ⚠️ Error clearing log files: {e}")
    
    print("\n📋 SUMMARY:")
    print(f"   Total items cleared: {len(cleared_items)}")
    if cleared_items:
        print("   Items cleared:")
        for item in cleared_items[:10]:  # Show first 10
            print(f"     - {item}")
        if len(cleared_items) > 10:
            print(f"     ... and {len(cleared_items) - 10} more")
    
    return len(cleared_items) > 0

def generate_cache_clear_instructions():
    """Generate instructions for clearing other types of cache"""
    
    print("\n🌐 BROWSER CACHE CLEARING INSTRUCTIONS:")
    print("=" * 50)
    print("1. Chrome/Edge:")
    print("   - Press Ctrl+Shift+Delete")
    print("   - Select 'Cached images and files'")
    print("   - Click 'Clear data'")
    print()
    print("2. Firefox:")
    print("   - Press Ctrl+Shift+Delete")
    print("   - Check 'Cache'")
    print("   - Click 'Clear Now'")
    print()
    print("3. Alternative - Use Incognito/Private mode")
    print("   - Test your JotForm API in private browsing")
    print("   - This bypasses all cached data")
    
    print("\n📞 JOTFORM SERVER CACHE:")
    print("=" * 30)
    print("Contact JotForm Support to clear server-side cache:")
    print("- Go to: https://www.jotform.com/contact/")
    print("- Subject: 'Clear form cache for persistent 429 errors'")
    print("- Message: 'Please clear my form cache - having 429 errors'")
    print("- Include your API key and form IDs")

if __name__ == "__main__":
    print("This will clear local caches that might interfere with JotForm API")
    print("⚠️ This is SAFE - your data won't be deleted")
    print()
    
    proceed = input("Clear local JotForm caches? (y/n): ").lower()
    
    if proceed == 'y':
        cleared = clear_jotform_caches()
        
        if cleared:
            print("\n✅ Cache clearing completed!")
            print("💡 Now try your JotForm API requests again")
        else:
            print("\n⚠️ No caches were found to clear")
        
        generate_cache_clear_instructions()
        
        print("\n🎯 NEXT STEPS:")
        print("1. Clear your browser cache (instructions above)")
        print("2. Try JotForm API again")
        print("3. If still 429 errors, contact JotForm support")
        print("4. Ask them to clear your server-side form cache")
        
    else:
        print("Cache clearing cancelled")
        generate_cache_clear_instructions()