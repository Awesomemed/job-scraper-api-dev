#!/usr/bin/env python3
"""
CGI wrapper for Flask application for cPanel deployment.
Place this file in the cgi-bin directory with execute permissions (755).
"""

import sys
import os

# Add the application directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and run the Flask application
from wsgiref.handlers import CGIHandler
from app import app

# Set up environment
os.environ['FLASK_ENV'] = 'production'

# Run the application
CGIHandler().run(app)