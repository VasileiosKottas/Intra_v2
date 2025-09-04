# Gmail SMTP Troubleshooting and Fix Script

import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

def test_gmail_smtp_step_by_step():
    """Test Gmail SMTP connection step by step to identify issues"""
    
    print("🔍 Gmail SMTP Troubleshooting")
    print("=" * 50)
    
    # Your credentials (remove spaces from app password)
    username = "vasiliskottas1@gmail.com"
    # Remove ALL spaces from the app password
    password = "nwqyhnwcekjkdiit"  # Original: "nwqy hnwc ekjk diit"
    
    print(f"Email: {username}")
    print(f"App Password: {password[:4]}{'*' * (len(password)-4)}")
    print()
    
    # Step 1: Test basic connection
    print("Step 1: Testing connection to Gmail SMTP server...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        print("✅ Connected to smtp.gmail.com:587")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Step 2: Test STARTTLS
    print("Step 2: Testing STARTTLS encryption...")
    try:
        context = ssl.create_default_context()
        server.starttls(context=context)
        print("✅ STARTTLS successful")
    except Exception as e:
        print(f"❌ STARTTLS failed: {e}")
        server.quit()
        return False
    
    # Step 3: Test authentication
    print("Step 3: Testing authentication...")
    try:
        server.login(username, password)
        print("✅ Authentication successful")
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("\n🔧 TROUBLESHOOTING SUGGESTIONS:")
        print("1. Verify 2-Factor Authentication is enabled on your Google account")
        print("2. Generate a NEW App Password:")
        print("   - Go to: https://myaccount.google.com/apppasswords")
        print("   - Delete the old App Password")
        print("   - Generate a new one for 'Mail'")
        print("3. Make sure you're using the App Password, NOT your regular Gmail password")
        print("4. Check if 'Less secure app access' is disabled (it should be)")
        server.quit()
        return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        server.quit()
        return False
    
    print("Step 4: Testing email send...")
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = "marsinta.pasai@windsorhillmortgages.co.uk"
        msg['Subject'] = "🧪 Gmail SMTP Test - Success!"
        
        body = """
        ✅ Gmail SMTP Test Successful!
        
        Your Gmail SMTP configuration is working correctly.
        This email was sent using:
        - Server: smtp.gmail.com:587
        - TLS: Enabled
        - Authentication: App Password
        
        You can now use this configuration for your Sales Dashboard automated reports.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send the email
        text = msg.as_string()
        server.sendmail(username, "marsinta.pasai@windsorhillmortgages.co.uk", text)
        print("✅ Test email sent successfully!")
        
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        server.quit()
        return False
    
    server.quit()
    print("\n🎉 All tests passed! Gmail SMTP is working correctly.")
    return True

def generate_new_app_password_instructions():
    """Print detailed instructions for generating a new App Password"""
    
    instructions = """
    📱 HOW TO GENERATE A NEW GMAIL APP PASSWORD
    ==========================================
    
    1. Go to your Google Account settings:
       https://myaccount.google.com
    
    2. Click on "Security" in the left sidebar
    
    3. Under "Signing in to Google", click "App passwords"
       (Note: You must have 2-Factor Authentication enabled)
    
    4. If you see an old "Mail" app password, DELETE it first
    
    5. Click "Generate" and select:
       - App: Mail
       - Device: Windows Computer (or whatever you prefer)
    
    6. Google will show you a 16-character password like: "abcd efgh ijkl mnop"
    
    7. IMPORTANT: Remove all spaces when using it in your code:
       - Displayed: "abcd efgh ijkl mnop"
       - Use in code: "abcdefghijklmnop"
    
    8. Update your environment variables:
       SMTP_USERNAME=vasiliskottas1@gmail.com
       SMTP_PASSWORD=your-new-16-char-password-no-spaces
    
    ⚠️  COMMON MISTAKES TO AVOID:
    - Don't use your regular Gmail password
    - Don't include spaces in the app password
    - Make sure 2FA is enabled on your account
    - Don't share your app password
    """
    
    print(instructions)

def test_with_corrected_password():
    """Test with the corrected password (no spaces)"""
    
    print("🔄 Testing with corrected password (spaces removed)...")
    
    # Corrected configuration
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    username = 'vasiliskottas1@gmail.com'
    password = 'nwqyhnwcekjkdiit'  # Removed spaces
    
    try:
        # Create connection
        context = ssl.create_default_context()
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls(context=context)
        
        # Test login
        server.login(username, password)
        print("✅ Login successful with corrected password!")
        
        server.quit()
        return True
        
    except Exception as e:
        print(f"❌ Still failing: {e}")
        return False

def update_environment_file():
    """Generate the correct .env file content"""
    
    env_content = """
# Corrected Gmail SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=vasiliskottas1@gmail.com
SMTP_PASSWORD=nwqyhnwcekjkdiit
"""
    
    print("📝 UPDATE YOUR .env FILE WITH THESE CORRECTED VALUES:")
    print("=" * 55)
    print(env_content.strip())
    print("=" * 55)
    
    # Try to write to .env file if it exists
    try:
        with open('.env', 'r') as f:
            existing_content = f.read()
        
        # Update SMTP_PASSWORD line
        lines = existing_content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('SMTP_PASSWORD='):
                updated_lines.append('SMTP_PASSWORD=nwqyhnwcekjkdiit')
                print("✅ Updated SMTP_PASSWORD in .env file")
            else:
                updated_lines.append(line)
        
        with open('.env', 'w') as f:
            f.write('\n'.join(updated_lines))
            
        print("✅ .env file updated automatically")
        
    except FileNotFoundError:
        print("ℹ️  .env file not found in current directory")
        print("Please create one or update manually")
    except Exception as e:
        print(f"⚠️  Could not update .env automatically: {e}")
        print("Please update manually")

if __name__ == "__main__":
    print("Gmail SMTP Issue Diagnosis and Fix")
    print("=" * 50)
    
    # First, try with the corrected password
    if test_with_corrected_password():
        print("\n🎉 ISSUE RESOLVED!")
        print("The problem was spaces in your App Password.")
        update_environment_file()
        
        # Run full test
        print("\n" + "=" * 50)
        test_gmail_smtp_step_by_step()
    else:
        print("\n❌ Password correction didn't work.")
        print("You likely need to generate a NEW App Password.")
        generate_new_app_password_instructions()
        
        print("\nAfter generating a new App Password, run this test again.")