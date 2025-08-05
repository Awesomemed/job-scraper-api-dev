"""
WSGI entry point for cPanel deployment using Passenger.
This file is used when deploying Python applications on cPanel with Passenger support.
"""

import sys
import os

# Add the application directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask application
from app import app as application

# Set up environment
os.environ['FLASK_ENV'] = 'production'

# Ensure the application runs
if __name__ == "__main__":
    application.run()