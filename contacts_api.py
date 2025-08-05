#!/usr/bin/env python3
"""
API para buscar y agregar contactos de empresas usando Apollo.io
Basado en apollo_contacts_enrichment.py
"""

from flask import Flask, request, jsonify
import requests
import json
import time
import re
from datetime import datetime
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import os
from threading import Lock
from collections import deque

app = Flask(__name__)

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')
    
file_handler = RotatingFileHandler('logs/contacts_api.log', maxBytes=10240000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Contacts API startup')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
APOLLO_API_KEY = os.environ.get('APOLLO_API_KEY', 'h93OetNklSHrDNgYo9nQng')
ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID', '1000.KP5I8V440G4BUMK7BKA4VGXTN58EPU')
ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET', 'fcb0113893df4bf97adcaec2f359302ddec729faa4')
ZOHO_REFRESH_TOKEN = os.environ.get('ZOHO_REFRESH_TOKEN', '1000.44be0b5623337acfd9706f54076fe99e.388905af35a5badc521cb2f58760487d')
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')

# Zoho configuration
ZOHO_DOMAIN = "https://www.zohoapis.com"
ACCOUNTS_MODULE = "Accounts"
CONTACTS_MODULE = "Contacts"

# Apollo rate limiting
API_CALLS_PER_MINUTE = 200
API_CALLS_PER_HOUR = 400
API_CALLS_PER_DAY = 2000

api_call_history_minute = deque(maxlen=API_CALLS_PER_MINUTE)
api_call_history_hour = deque(maxlen=API_CALLS_PER_HOUR)
api_call_history_day = deque(maxlen=API_CALLS_PER_DAY)
api_call_lock = Lock()

# Statistics
api_stats = {
    "total_calls": 0,
    "total_contacts_found": 0,
    "total_contacts_created": 0,
    "total_contacts_duplicated": 0,
    "total_errors": 0
}

# API Key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            api_key = request.headers.get('x-api-key')
        if not api_key:
            api_key = request.args.get('api_key')
        
        if not api_key:
            app.logger.warning("No API key provided in request")
            return jsonify({
                'error': 'API key is required',
                'message': 'Please provide API key in X-API-Key header or api_key query parameter'
            }), 401
        
        if api_key != API_KEY:
            app.logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        app.logger.info("API key validated successfully")
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
def get_access_token():
    """Get Zoho access token using refresh token."""
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        'refresh_token': ZOHO_REFRESH_TOKEN,
        'client_id': ZOHO_CLIENT_ID,
        'client_secret': ZOHO_CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }
    
    app.logger.info("Requesting Zoho access token")
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        app.logger.info("Access token obtained successfully")
        return response.json()['access_token']
    else:
        error_msg = f"Error getting token: Code {response.status_code}, Response: {response.text}"
        app.logger.error(error_msg)
        raise Exception(error_msg)

def controlar_tasa_api():
    """Control Apollo API rate limits."""
    with api_call_lock:
        current_time = time.time()
        
        # Clean old entries
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        # Clean histories
        while api_call_history_minute and api_call_history_minute[0] < minute_ago:
            api_call_history_minute.popleft()
        while api_call_history_hour and api_call_history_hour[0] < hour_ago:
            api_call_history_hour.popleft()
        while api_call_history_day and api_call_history_day[0] < day_ago:
            api_call_history_day.popleft()
        
        # Check limits
        if len(api_call_history_minute) >= API_CALLS_PER_MINUTE:
            wait_time = 60 - (current_time - api_call_history_minute[0])
            app.logger.warning(f"Rate limit per minute reached. Waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
        
        if len(api_call_history_hour) >= API_CALLS_PER_HOUR:
            wait_time = 3600 - (current_time - api_call_history_hour[0])
            app.logger.warning(f"Rate limit per hour reached. Waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
        
        if len(api_call_history_day) >= API_CALLS_PER_DAY:
            wait_time = 86400 - (current_time - api_call_history_day[0])
            app.logger.error(f"Daily rate limit reached. Waiting {wait_time:.1f} seconds")
            raise Exception("Daily Apollo API limit reached")
        
        # Add current call
        api_call_history_minute.append(current_time)
        api_call_history_hour.append(current_time)
        api_call_history_day.append(current_time)
        api_stats["total_calls"] += 1

def obtener_dominio_desde_url(url):
    """Extract domain from URL."""
    if not url:
        return None
    
    try:
        url = url.lower().strip()
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        domain = url.split('/')[0]
        domain = domain.split('?')[0].split('#')[0]
        
        if domain and '.' in domain and len(domain) > 3:
            return domain
        
        return None
    except Exception as e:
        app.logger.error(f"Error extracting domain from {url}: {e}")
        return None

def buscar_contactos_apollo(domain, max_contacts=10, filter_type="all"):
    """
    Search contacts in Apollo.io
    
    Args:
        domain: Company domain
        max_contacts: Maximum number of contacts to retrieve
        filter_type: "all", "managers", "executives"
    """
    if not domain:
        return []
    
    app.logger.info(f"Searching Apollo contacts for domain: {domain}, filter: {filter_type}")
    
    controlar_tasa_api()
    
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY
    }
    
    payload = {
        "q_organization_domains_list": [domain],
        "contact_email_status": ["verified", "unverified", "likely_to_engage"],
        "page": 1,
        "per_page": max_contacts,
    }
    
    # Apply filters based on type
    if filter_type == "managers":
        payload["person_titles[]"] = ["manager"]
        payload["include_similar_titles"] = True
    elif filter_type == "executives":
        payload["person_seniorities"] = ["director", "manager", "c_suite"]
        payload["person_titles[]"] = [
            "manager", "director", "president", "CEO", "CFO", "CTO", 
            "CMO", "COO", "founder", "owner", "partner"
        ]
        payload["include_similar_titles"] = True
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            apollo_contacts = data.get('people', [])
            
            valid_contacts = []
            for person in apollo_contacts:
                email = person.get('email')
                
                if not email or not person.get('first_name') or not person.get('last_name'):
                    continue
                
                if "email_not_unlocked@" in email:
                    continue
                
                organization = person.get('organization', {}) or {}
                
                contact_data = {
                    "apollo_id": person.get('id'),
                    "first_name": person.get('first_name'),
                    "last_name": person.get('last_name'),
                    "email": email,
                    "title": person.get('title'),
                    "seniority": person.get('seniority'),
                    "phone": person.get('phone'),
                    "linkedin_url": person.get('linkedin_url'),
                    "organization_name": organization.get('name', 'N/A'),
                    "organization_id": organization.get('id'),
                    "departments": person.get('departments', []),
                    "city": person.get('city'),
                    "state": person.get('state'),
                    "country": person.get('country'),
                    "apollo_person_url": f"https://app.apollo.io/#/people/{person.get('id')}" if person.get('id') else None
                }
                
                valid_contacts.append(contact_data)
            
            api_stats["total_contacts_found"] += len(valid_contacts)
            return valid_contacts
            
        elif response.status_code == 429:
            app.logger.warning(f"Apollo API rate limit exceeded")
            raise Exception("Apollo API rate limit exceeded")
        else:
            app.logger.error(f"Apollo API error: {response.status_code}")
            api_stats["total_errors"] += 1
            return []
            
    except Exception as e:
        app.logger.error(f"Exception searching Apollo contacts: {e}")
        api_stats["total_errors"] += 1
        raise

def verificar_contacto_existe_zoho(access_token, email, account_id):
    """Check if contact already exists in Zoho."""
    if not email:
        return False
    
    url = f"{ZOHO_DOMAIN}/crm/v2/{CONTACTS_MODULE}/search"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    params = {
        'criteria': f'Email:equals:{email}',
        'fields': 'id,Email,Account_Name'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('data', [])
            
            if contacts:
                app.logger.info(f"Contact with email {email} already exists")
                api_stats["total_contacts_duplicated"] += 1
                return True
                
        elif response.status_code == 204:
            return False
            
    except Exception as e:
        app.logger.error(f"Error checking existing contact: {e}")
    
    return False

def crear_contacto_zoho(access_token, contact_data, account_id):
    """Create contact in Zoho CRM."""
    url = f"{ZOHO_DOMAIN}/crm/v2/{CONTACTS_MODULE}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    zoho_contact = {
        "data": [{
            "First_Name": contact_data['first_name'],
            "Last_Name": contact_data['last_name'],
            "Email": contact_data['email'],
            "Account_Name": {"id": account_id},
            "Title": contact_data.get('title'),
            "Phone": contact_data.get('phone'),
            "LinkedIn": contact_data.get('linkedin_url'),
            "Mailing_City": contact_data.get('city'),
            "Mailing_State": contact_data.get('state'),
            "Mailing_Country": contact_data.get('country'),
            "Department": ', '.join(contact_data.get('departments', [])) if contact_data.get('departments') else None,
            "Lead_Source": "Apollo.io",
            "Apollo_ID": contact_data.get('apollo_id'),
            "Apollo_URL": contact_data.get('apollo_person_url')
        }]
    }
    
    # Remove None values
    zoho_contact["data"][0] = {k: v for k, v in zoho_contact["data"][0].items() if v is not None}
    
    try:
        response = requests.post(url, headers=headers, json=zoho_contact)
        
        if response.status_code == 201:
            result = response.json()
            contact_id = result['data'][0]['details']['id']
            app.logger.info(f"Contact created successfully: {contact_id}")
            api_stats["total_contacts_created"] += 1
            return contact_id
        else:
            app.logger.error(f"Error creating contact: {response.status_code} - {response.text}")
            api_stats["total_errors"] += 1
            return None
            
    except Exception as e:
        app.logger.error(f"Exception creating contact: {e}")
        api_stats["total_errors"] += 1
        return None

# API Routes
@app.route('/')
def index():
    return jsonify({
        'status': 'active',
        'service': 'Contacts Enrichment API',
        'version': '1.0.0',
        'endpoints': {
            '/search_contacts': 'POST - Search contacts for a company',
            '/enrich_company': 'POST - Enrich company with contacts',
            '/stats': 'GET - Get API statistics',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/stats')
@require_api_key
def stats():
    """Get API usage statistics."""
    return jsonify({
        'apollo_api': {
            'total_calls': api_stats['total_calls'],
            'minute_usage': len(api_call_history_minute),
            'hour_usage': len(api_call_history_hour),
            'day_usage': len(api_call_history_day),
            'limits': {
                'per_minute': API_CALLS_PER_MINUTE,
                'per_hour': API_CALLS_PER_HOUR,
                'per_day': API_CALLS_PER_DAY
            }
        },
        'contacts': {
            'total_found': api_stats['total_contacts_found'],
            'total_created': api_stats['total_contacts_created'],
            'total_duplicated': api_stats['total_contacts_duplicated']
        },
        'errors': api_stats['total_errors'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/search_contacts', methods=['POST'])
@require_api_key
def search_contacts():
    """
    Search contacts for a company domain.
    
    Expected JSON payload:
    {
        "domain": "example.com",
        "max_contacts": 10,
        "filter_type": "all" | "managers" | "executives"
    }
    """
    try:
        data = request.get_json()
        
        domain = data.get('domain')
        if not domain:
            return jsonify({'error': 'Domain is required'}), 400
        
        max_contacts = int(data.get('max_contacts', 10))
        filter_type = data.get('filter_type', 'all')
        
        if filter_type not in ['all', 'managers', 'executives']:
            return jsonify({'error': 'Invalid filter_type. Use: all, managers, or executives'}), 400
        
        app.logger.info(f"Searching contacts for domain: {domain}")
        
        # Search contacts in Apollo
        contacts = buscar_contactos_apollo(domain, max_contacts, filter_type)
        
        return jsonify({
            'success': True,
            'domain': domain,
            'filter_type': filter_type,
            'contacts_found': len(contacts),
            'contacts': contacts,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in search_contacts: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/enrich_company', methods=['POST'])
@require_api_key
def enrich_company():
    """
    Enrich a Zoho company with contacts from Apollo.
    
    Expected JSON payload:
    {
        "company_id": "zoho_company_id",
        "company_name": "Company Name",
        "company_website": "https://example.com",
        "max_contacts": 10,
        "filter_type": "all" | "managers" | "executives",
        "skip_duplicates": true
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({'error': 'company_id is required'}), 400
        
        company_website = data.get('company_website')
        if not company_website:
            return jsonify({'error': 'company_website is required'}), 400
        
        company_name = data.get('company_name', 'Unknown')
        max_contacts = int(data.get('max_contacts', 10))
        filter_type = data.get('filter_type', 'all')
        skip_duplicates = data.get('skip_duplicates', True)
        
        app.logger.info(f"Enriching company: {company_name} (ID: {company_id})")
        
        # Extract domain from website
        domain = obtener_dominio_desde_url(company_website)
        if not domain:
            return jsonify({'error': 'Could not extract domain from website URL'}), 400
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Search contacts in Apollo
        contacts = buscar_contactos_apollo(domain, max_contacts, filter_type)
        
        if not contacts:
            return jsonify({
                'success': True,
                'message': 'No contacts found for this domain',
                'domain': domain,
                'contacts_found': 0,
                'contacts_created': 0,
                'timestamp': datetime.now().isoformat()
            })
        
        # Create contacts in Zoho
        created_count = 0
        skipped_count = 0
        errors = []
        
        for contact in contacts:
            try:
                # Check if contact already exists
                if skip_duplicates and verificar_contacto_existe_zoho(access_token, contact['email'], company_id):
                    skipped_count += 1
                    app.logger.info(f"Skipped duplicate contact: {contact['email']}")
                    continue
                
                # Create contact
                contact_id = crear_contacto_zoho(access_token, contact, company_id)
                if contact_id:
                    created_count += 1
                else:
                    errors.append(f"Failed to create contact: {contact['email']}")
                    
            except Exception as e:
                error_msg = f"Error processing contact {contact.get('email', 'unknown')}: {str(e)}"
                app.logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            'success': True,
            'company': {
                'id': company_id,
                'name': company_name,
                'domain': domain
            },
            'summary': {
                'contacts_found': len(contacts),
                'contacts_created': created_count,
                'contacts_skipped': skipped_count,
                'errors': len(errors)
            },
            'errors': errors if errors else None,
            'timestamp': datetime.now().isoformat()
        }
        
        app.logger.info(f"Enrichment completed: {result['summary']}")
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in enrich_company: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)