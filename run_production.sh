#!/bin/bash

# Run the API with Gunicorn for production with extended timeout

echo "Starting Job Scraper API with extended timeout settings..."

# Export environment variables if .env file exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Run with gunicorn using configuration file
gunicorn -c gunicorn_config.py app:app

# Alternative: Run with specific timeout directly
# gunicorn --workers 4 --timeout 1800 --bind 0.0.0.0:5000 app:app