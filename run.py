"""
Development entry point for the Sales Dashboard application
"""

import os
from dotenv import load_dotenv
from app.main import SalesDashboardApp

# Load environment variables from .env file
load_dotenv()

def main():
    """Main function to run the development server"""
    # Create and run application
    app = SalesDashboardApp('development')
    
    print(" Sales Dashboard starting in development mode...")
    print(" Dashboard available at http://localhost:5000")
    print(" Default master login: username='master', password='master123'")
    
    # Run development server
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )

if __name__ == '__main__':
    main()