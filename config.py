import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = False
    TESTING = False
    
    # API Authentication
    API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')
    
    # Apollo.io Configuration
    APOLLO_API_KEY = os.environ.get('APOLLO_API_KEY', 'h93OetNklSHrDNgYo9nQng')
    
    # Zoho CRM Configuration
    ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID', '1000.KP5I8V440G4BUMK7BKA4VGXTN58EPU')
    ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET', 'fcb0113893df4bf97adcaec2f359302ddec729faa4')
    ZOHO_REFRESH_TOKEN = os.environ.get('ZOHO_REFRESH_TOKEN', '1000.44be0b5623337acfd9706f54076fe99e.388905af35a5badc521cb2f58760487d')
    ZOHO_DOMAIN = os.environ.get('ZOHO_DOMAIN', 'https://www.zohoapis.com')
    
    # Zoho Module Names
    COMPANY_MODULE = "Accounts"
    JOBS_MODULE = "Jobs"
    JUNCTION_MODULE = "Account_X_Job"
    COMPANY_RELATION_FIELD = "Related_company"
    
    # Job Scraping Configuration
    DEFAULT_SEARCH_TERM = "Call Center"
    DEFAULT_COUNTRY = "USA"
    DEFAULT_RESULTS_WANTED = 50
    DEFAULT_HOURS_OLD = 1440  # 24 hours
    
    # Rate Limiting
    MIN_DELAY_SECONDS = 0.5
    MAX_DELAY_SECONDS = 1.5
    
    # Logging
    LOG_FILE = 'logs/api.log'
    LOG_MAX_BYTES = 10240000  # 10MB
    LOG_BACKUP_COUNT = 10

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Override with production values
    SECRET_KEY = os.environ.get('SECRET_KEY')
    API_KEY = os.environ.get('API_KEY')
    
    # Ensure all required environment variables are set
    @classmethod
    def init_app(cls, app):
        # Validate required environment variables
        required_vars = [
            'SECRET_KEY',
            'API_KEY',
            'APOLLO_API_KEY',
            'ZOHO_CLIENT_ID',
            'ZOHO_CLIENT_SECRET',
            'ZOHO_REFRESH_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}