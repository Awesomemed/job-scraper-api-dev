#!/usr/bin/env python3
"""
Script para ejecutar la API en modo desarrollo
"""

import os
import sys

# Asegurar que las variables de entorno se cargan
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# Importar y ejecutar la aplicación
from app import app

if __name__ == '__main__':
    print("Starting Job Scraper API in development mode...")
    print(f"API Key configured: {os.environ.get('API_KEY', 'NOT SET')[:10]}...")
    print("\nTest endpoints:")
    print("- GET  http://localhost:5000/health (no auth required)")
    print("- GET  http://localhost:5000/test-auth (requires API key)")
    print("- POST http://localhost:5000/scrape (requires API key)")
    print("\nPress CTRL+C to stop the server")
    
    app.run(host='0.0.0.0', port=5000, debug=True)