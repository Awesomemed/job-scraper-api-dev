from flask import Flask, request, jsonify
import pandas as pd
from jobspy import scrape_jobs
import time
import random
import requests
import json
import os
import re
from datetime import datetime, date
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import threading
import uuid
from collections import defaultdict

app = Flask(__name__)

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')
    
file_handler = RotatingFileHandler('logs/api.log', maxBytes=10240000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Job Scraper API startup')
job_status = defaultdict(dict)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configuration - Load from environment variables or config file
APOLLO_API_KEY = os.environ.get('APOLLO_API_KEY', 'h93OetNklSHrDNgYo9nQng')
ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID', '1000.KP5I8V440G4BUMK7BKA4VGXTN58EPU')
ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET', 'fcb0113893df4bf97adcaec2f359302ddec729faa4')
ZOHO_REFRESH_TOKEN = os.environ.get('ZOHO_REFRESH_TOKEN', '1000.44be0b5623337acfd9706f54076fe99e.388905af35a5badc521cb2f58760487d')
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')

app.logger.info(f'API_KEY configured: {API_KEY[:10]}...')

# Zoho configuration
ZOHO_DOMAIN = "https://www.zohoapis.com"
COMPANY_MODULE = "Accounts"
JOBS_MODULE = "Jobs"
COMPANY_RELATION_FIELD = "Related_company"

# Función para procesar jobs en background
def process_scraping_job(job_id, data, access_token):
    """Procesa el scraping en un thread separado"""
    try:
        # Actualizar estado
        job_status[job_id]['status'] = 'processing'
        job_status[job_id]['start_time'] = datetime.now().isoformat()
        
        # Extraer parámetros
        search_term = data.get('search_term', 'Call Center')
        location = data.get('location', '')
        results_wanted = int(data.get('results_wanted', 50))
        hours_old = int(data.get('hours_old', 1440))
        country = data.get('country', 'USA')
        
        app.logger.info(f"Job {job_id}: Starting background scraping")
        
        # Scrape jobs from Indeed
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=country,
        )
        
        app.logger.info(f"Job {job_id}: Found {len(jobs)} jobs")
        
        # Filter columns
        columnas_deseadas = ['id', 'title', 'company', 'location', 'job_url', 'job_url_direct', 
                           'company_url', 'company_url_direct', 'date_posted', 'description']
        
        for col in columnas_deseadas:
            if col not in jobs.columns:
                jobs[col] = None
        
        jobs_filtrados = jobs[columnas_deseadas].copy()
        jobs_filtrados = jobs_filtrados.fillna('')
        
        # Process statistics
        contador_insertados = 0
        contador_omitidos = 0
        contador_empresas_existentes = 0
        contador_empresas_nuevas = 0
        
        # Company cache
        cache_empresas = {}
        
        # Actualizar progreso
        total_jobs = len(jobs_filtrados)
        job_status[job_id]['total_jobs'] = total_jobs
        job_status[job_id]['processed_jobs'] = 0
        
        # Process each job
        for index, row in jobs_filtrados.iterrows():
            try:
                company_name = row['company'].strip()
                company_website = row['company_url_direct'].strip()
                
                if not company_name:
                    company_name = "Unknown Company"
                
                if not company_website:
                    company_website = ""
                
                # Check company cache
                if company_name in cache_empresas:
                    company_id = cache_empresas[company_name]
                else:
                    # Search for company in Zoho
                    company_id = buscar_empresa_en_zoho(access_token, company_name)
                    
                    # Create if not exists
                    if not company_id:
                        try:
                            company_id = crear_empresa_en_zoho(access_token, company_name, company_website)
                            contador_empresas_nuevas += 1
                        except Exception as e:
                            app.logger.error(f"Job {job_id}: Error creating company '{company_name}': {e}")
                            continue
                    else:
                        contador_empresas_existentes += 1
                    
                    # Save to cache
                    cache_empresas[company_name] = company_id
                
                # Create job in Zoho
                job_data_dict = row.to_dict()
                
                if crear_trabajo_en_zoho(access_token, job_data_dict, company_id):
                    contador_insertados += 1
                else:
                    contador_omitidos += 1
                
                # Actualizar progreso
                job_status[job_id]['processed_jobs'] = index + 1
                job_status[job_id]['jobs_created'] = contador_insertados
                job_status[job_id]['jobs_skipped'] = contador_omitidos
                
                # Rate limiting
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                app.logger.error(f"Job {job_id}: Error processing job: {e}")
        
        # Actualizar resultado final
        job_status[job_id]['status'] = 'completed'
        job_status[job_id]['end_time'] = datetime.now().isoformat()
        job_status[job_id]['summary'] = {
            'total_jobs_found': len(jobs_filtrados),
            'jobs_created': contador_insertados,
            'jobs_skipped': contador_omitidos,
            'existing_companies_used': contador_empresas_existentes,
            'new_companies_created': contador_empresas_nuevas
        }
        
        app.logger.info(f"Job {job_id}: Completed - {job_status[job_id]['summary']}")
        
    except Exception as e:
        app.logger.error(f"Job {job_id}: Fatal error - {e}")
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = str(e)
        job_status[job_id]['end_time'] = datetime.now().isoformat()

# API Key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log incoming request
        app.logger.info(f"Incoming request to {request.path}")
        
        # Get API key from headers or query params
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            api_key = request.headers.get('x-api-key')  # Try lowercase
        if not api_key:
            api_key = request.args.get('api_key')
        
        # Log API key status
        if not api_key:
            app.logger.warning("No API key provided in request")
            return jsonify({
                'error': 'API key is required',
                'message': 'Please provide API key in X-API-Key header or api_key query parameter'
            }), 401
        
        # Check if API key matches
        if api_key != API_KEY:
            app.logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        app.logger.info("API key validated successfully")
        return f(*args, **kwargs)
    return decorated_function

# Helper functions (imported from test.py)
def ensure_serializable(data):
    """Ensure all values in a dictionary are JSON serializable."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = ensure_serializable(value)
        return result
    elif isinstance(data, list):
        return [ensure_serializable(item) for item in data]
    elif hasattr(data, 'strftime'):
        return data.strftime('%Y-%m-%d')
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        return str(data)

def obtener_dominio_desde_url(url):
    """Extract base domain from URL."""
    if not url or not isinstance(url, str):
        return None
    
    try:
        url = url.lower().strip()
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        dominio = url.split('/')[0]
        dominio = dominio.split('?')[0].split('#')[0]
        dominio = dominio.strip()
        
        if dominio and '.' in dominio and len(dominio) > 3:
            return dominio
        
        return None
    except Exception as e:
        app.logger.error(f"Error processing URL {url}: {e}")
        return None

def construir_apollo_url(apollo_id):
    """Build Apollo URL for a specific company."""
    if apollo_id:
        return f"https://app.apollo.io/#/organizations/{apollo_id}"
    return ""

def enriquecer_empresa_apollo(dominio):
    """Enrich company information using Apollo.io API."""
    app.logger.info(f"Enriching data with Apollo.io for domain: {dominio}")
    
    url = "https://api.apollo.io/api/v1/organizations/enrich"
    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY
    }
    payload = {"domain": dominio}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            organization = data.get('organization')
            
            if organization:
                apollo_id = organization.get('id')
                apollo_url = construir_apollo_url(apollo_id)
                
                resultado = {
                    'phone': organization.get('phone', ''),
                    'facebook_url': organization.get('facebook_url', ''),
                    'linkedin_url': organization.get('linkedin_url', ''),
                    'twitter_url': organization.get('twitter_url', ''),
                    'industry': organization.get('industry', ''),
                    'annual_revenue': organization.get('annual_revenue', ''),
                    'estimated_num_employees': organization.get('estimated_num_employees', ''),
                    'apollo_url': apollo_url,
                    'apollo_id': apollo_id
                }
                
                app.logger.info(f"Apollo.io data found for domain: {dominio}")
                return resultado
            else:
                app.logger.warning(f"No results found in Apollo for domain: {dominio}")
                return None
        else:
            app.logger.error(f"Apollo API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        app.logger.error(f"Error during Apollo enrichment: {e}")
        return None

def get_access_token():
    """Get access token using refresh token."""
    url = f"https://accounts.zoho.com/oauth/v2/token"
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

def verificar_id_empresa(access_token, company_id):
    """Verify that company ID is valid in Accounts module."""
    url = f"{ZOHO_DOMAIN}/crm/v2/{COMPANY_MODULE}/{company_id}"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            app.logger.info(f"Company ID {company_id} verified successfully")
            return True
        else:
            app.logger.error(f"Error verifying company ID: {response.status_code}")
            return False
    except Exception as e:
        app.logger.error(f"Error verifying company ID: {e}")
        return False

def buscar_empresa_en_zoho(access_token, company_name):
    """Search for company by name in Zoho CRM Accounts module."""
    url = f"{ZOHO_DOMAIN}/crm/v2/{COMPANY_MODULE}/search"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    query_params = {'criteria': f"Account_Name:equals:{company_name}"}
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                company_id = data['data'][0]['id']
                app.logger.info(f"Company '{company_name}' found with ID: {company_id}")
                return company_id
        
        # Try with contains if exact match fails
        query_params = {'criteria': f"Account_Name:contains:{company_name}"}
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                for company in data['data']:
                    if company['Account_Name'].lower() == company_name.lower():
                        company_id = company['id']
                        app.logger.info(f"Company '{company_name}' found with ID: {company_id}")
                        return company_id
    except Exception as e:
        app.logger.error(f"Error searching company: {e}")
    
    app.logger.info(f"Company '{company_name}' not found in Zoho")
    return None

def crear_empresa_en_zoho(access_token, company_name, company_website):
    """Create new company in Zoho CRM Accounts module and enrich with Apollo."""
    url = f"{ZOHO_DOMAIN}/crm/v2/{COMPANY_MODULE}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "data": [{
            "Account_Name": company_name,
            "Website": company_website,
            "Account_Source": "Indeed",
            "Account_Type": "COLD"
        }]
    }
    
    # Try to enrich with Apollo if website exists
    apollo_data = None
    if company_website:
        dominio = obtener_dominio_desde_url(company_website)
        if dominio:
            apollo_data = enriquecer_empresa_apollo(dominio)
            
            if apollo_data:
                # Add Apollo fields to company data
                if apollo_data.get('phone'):
                    data["data"][0]["Phone"] = apollo_data['phone']
                if apollo_data.get('linkedin_url'):
                    data["data"][0]["Linkedin_Page"] = apollo_data['linkedin_url']
                if apollo_data.get('facebook_url'):
                    data["data"][0]["Facebook"] = apollo_data['facebook_url']
                if apollo_data.get('twitter_url'):
                    data["data"][0]["X_Twitter"] = apollo_data['twitter_url']
                if apollo_data.get('industry'):
                    data["data"][0]["Industry"] = apollo_data['industry']
                if apollo_data.get('estimated_num_employees'):
                    data["data"][0]["Employees"] = apollo_data['estimated_num_employees']
                if apollo_data.get('annual_revenue'):
                    data["data"][0]["Annual_Revenue"] = apollo_data['annual_revenue']
                if apollo_data.get('apollo_url'):
                    data["data"][0]["Apollo_URL"] = apollo_data['apollo_url']
                
                data["data"][0]["Last_Enriched"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["data"][0]["Data_Source"] = "Indeed + Apollo.io"
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            result = response.json()
            if result.get('data') and len(result['data']) > 0:
                company_id = result['data'][0]['details']['id']
                app.logger.info(f"Company '{company_name}' created with ID: {company_id}")
                return company_id
            else:
                raise Exception(f"Unexpected response creating company: {response.text}")
        else:
            raise Exception(f"Error creating company: Code {response.status_code} - {response.text}")
    except Exception as e:
        app.logger.error(f"Error creating company: {e}")
        raise

def buscar_trabajo_en_zoho(access_token, indeed_id):
    """Check if job with Indeed ID already exists in Zoho."""
    url = f"{ZOHO_DOMAIN}/crm/v2/{JOBS_MODULE}/search"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    query_params = {'criteria': f"ID_Indeed:equals:{indeed_id}"}
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                return True
    except Exception as e:
        app.logger.error(f"Error searching job: {e}")
    
    return False

# Function removed - Apollo enrichment is only for companies, not jobs

def crear_trabajo_en_zoho(access_token, job_data, company_id):
    """Create new job in Zoho CRM Jobs module."""
    # Check if job already exists
    indeed_id = job_data['id']
    if buscar_trabajo_en_zoho(access_token, indeed_id):
        app.logger.info(f"Job with Indeed ID '{indeed_id}' already exists. Skipping.")
        return False
    
    JUNCTION_MODULE = "Account_X_Job"
    
    jobs_url = f"{ZOHO_DOMAIN}/crm/v2/{JOBS_MODULE}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Verify company exists
    if not verificar_id_empresa(access_token, company_id):
        app.logger.error(f"Company ID {company_id} is not valid")
        return False
    
    # Create job data
    job_data_dict = {
        "data": [{
            "Name": job_data['title'],
            "ID_Indeed": indeed_id,
            "Location": job_data['location'],
            "Company_URL": job_data['company_url_direct'],
            # Establecer la relación con la empresa de múltiples formas
            "Account": company_id,  # Campo principal de relación
            "Related_company": {    # Campo adicional de relación
                "id": company_id
            },
            "Lookup_1": {          # Campo Lookup_1 con ID de empresa
                "id": company_id
            }
        }]
    }
    
    app.logger.info(f"Creating job with company relationship - Company ID: {company_id}")
    
    # Apollo enrichment removed - only enrich companies, not jobs
    
    # Add optional fields
    if 'job_url' in job_data and job_data['job_url']:
        job_data_dict["data"][0]["Job_URL"] = job_data['job_url']
    
    if 'job_url_direct' in job_data and job_data['job_url_direct']:
        job_data_dict["data"][0]["Job_URL_Direct"] = job_data['job_url_direct']
    
    if 'company' in job_data and job_data['company']:
        job_data_dict["data"][0]["Company"] = job_data['company']
    
    if 'company_url' in job_data and job_data['company_url']:
        job_data_dict["data"][0]["Company_URL_Indeed"] = job_data['company_url']
    
    if 'description' in job_data and job_data['description']:
        description = job_data['description']
        if len(description) > 1000:
            description = description[:997] + "..."
        job_data_dict["data"][0]["Description"] = description
    
    job_data_dict["data"][0]["Date_Found"] = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure data is serializable
    safe_data = ensure_serializable(job_data_dict)
    
    try:
        # Create job
        job_response = requests.post(jobs_url, headers=headers, json=safe_data)
        
        if job_response.status_code != 201:
            app.logger.error(f"Error creating job: {job_response.status_code} - {job_response.text}")
            
            # Try with minimal data
            minimal_data = {
                "data": [{
                    "Name": job_data['title'],
                    "Account": {"id": company_id}
                }]
            }
            
            minimal_response = requests.post(jobs_url, headers=headers, json=minimal_data)
            if minimal_response.status_code != 201:
                app.logger.error(f"Also failed with minimal data: {minimal_response.text}")
                return False
            
            job_response = minimal_response
        
        job_id = job_response.json()['data'][0]['details']['id']
        app.logger.info(f"Job created with ID: {job_id}")
        
        # Try to create junction record with correct field names
        try:
            junction_url = f"{ZOHO_DOMAIN}/crm/v2/{JUNCTION_MODULE}"
            junction_data = {
                "data": [{
                    "Related_Job": {"id": job_id},
                    "Related_company": {"id": company_id}
                }]
            }
            
            app.logger.info(f"Creating junction record with data: {junction_data}")
            junction_response = requests.post(junction_url, headers=headers, json=junction_data)
            
            if junction_response.status_code == 201:
                app.logger.info("✅ Junction record created successfully in Account_X_Job")
            else:
                app.logger.warning(f"Failed to create junction record: {junction_response.status_code}")
                if junction_response.status_code == 202:
                    try:
                        error_details = junction_response.json()
                        app.logger.error(f"Junction error details: {error_details}")
                    except:
                        pass
        except Exception as e:
            app.logger.warning(f"Error creating junction record: {e}")
        
        return True
    except Exception as e:
        app.logger.error(f"Error creating job: {e}")
        return False

# API Routes
@app.route('/')
def index():
    return jsonify({
        'status': 'active',
        'service': 'Job Scraper API with Apollo Contacts',
        'version': '1.2.0',
        'endpoints': {
            '/scrape': 'POST - Scrape jobs from Indeed',
            '/health': 'GET - Health check',
            '/stats': 'GET - Get API statistics',
            '/search_contacts': 'POST - Search contacts for a domain',
            '/enrich_contacts': 'POST - Enrich company with Apollo contacts',
            '/analyze_companies': 'GET - Analyze which companies have/don\'t have contacts',
            '/enrich_companies_without_contacts': 'POST - Bulk enrich companies without contacts'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test-auth', methods=['GET', 'POST'])
@require_api_key
def test_auth():
    """Test endpoint to verify API key authentication is working"""
    return jsonify({
        'status': 'success',
        'message': 'Authentication successful',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
@require_api_key
def scrape_jobs_endpoint():
    """
    Main endpoint for scraping jobs and saving to Zoho.
    
    Expected JSON payload:
    {
        "search_term": "Call Center",
        "location": "Arizona, USA",
        "results_wanted": 50,
        "hours_old": 1440,
        "country": "USA"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        search_term = data.get('search_term', 'Call Center')
        location = data.get('location', '')
        results_wanted = int(data.get('results_wanted', 50))
        hours_old = int(data.get('hours_old', 1440))
        country = data.get('country', 'USA')
        
        app.logger.info(f"Starting job scrape: search_term={search_term}, location={location}, results={results_wanted}")
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Scrape jobs from Indeed
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed=country,
        )
        
        app.logger.info(f"Found {len(jobs)} jobs from Indeed")
        
        # Filter columns
        columnas_deseadas = ['id', 'title', 'company', 'location', 'job_url', 'job_url_direct', 
                           'company_url', 'company_url_direct', 'date_posted', 'description']
        
        for col in columnas_deseadas:
            if col not in jobs.columns:
                jobs[col] = None
        
        jobs_filtrados = jobs[columnas_deseadas].copy()
        jobs_filtrados = jobs_filtrados.fillna('')
        
        # Process statistics
        contador_insertados = 0
        contador_omitidos = 0
        contador_empresas_existentes = 0
        contador_empresas_nuevas = 0
        
        # Company cache
        cache_empresas = {}
        
        # Process each job
        for index, row in jobs_filtrados.iterrows():
            try:
                company_name = row['company'].strip()
                company_website = row['company_url_direct'].strip()
                
                if not company_name:
                    company_name = "Unknown Company"
                
                if not company_website:
                    company_website = ""
                
                # Check company cache
                if company_name in cache_empresas:
                    company_id = cache_empresas[company_name]
                else:
                    # Search for company in Zoho
                    company_id = buscar_empresa_en_zoho(access_token, company_name)
                    
                    # Create if not exists
                    if not company_id:
                        try:
                            company_id = crear_empresa_en_zoho(access_token, company_name, company_website)
                            contador_empresas_nuevas += 1
                        except Exception as e:
                            app.logger.error(f"Error creating company '{company_name}': {e}")
                            continue
                    else:
                        contador_empresas_existentes += 1
                    
                    # Save to cache
                    cache_empresas[company_name] = company_id
                
                # Create job in Zoho
                job_data_dict = row.to_dict()
                
                if crear_trabajo_en_zoho(access_token, job_data_dict, company_id):
                    contador_insertados += 1
                else:
                    contador_omitidos += 1
                
                # Rate limiting
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                app.logger.error(f"Error processing job: {e}")
        
        # Return results
        result = {
            'success': True,
            'summary': {
                'total_jobs_found': len(jobs_filtrados),
                'jobs_created': contador_insertados,
                'jobs_skipped': contador_omitidos,
                'existing_companies_used': contador_empresas_existentes,
                'new_companies_created': contador_empresas_nuevas
            },
            'timestamp': datetime.now().isoformat()
        }
        
        app.logger.info(f"Scraping completed: {result['summary']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        app.logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/stats')
@require_api_key
def stats():
    """Get API usage statistics."""
    # In a production environment, you would fetch this from a database
    return jsonify({
        'total_requests': 0,
        'successful_scrapes': 0,
        'failed_scrapes': 0,
        'timestamp': datetime.now().isoformat()
    })

# Contact enrichment functions
def buscar_contactos_apollo(domain, max_contacts=10, filter_type="all"):
    """Search contacts in Apollo.io"""
    if not domain:
        return []
    
    app.logger.info(f"Searching Apollo contacts for domain: {domain}, filter: {filter_type}")
    
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY
    }
    
    payload = {
        "q_organization_domains": domain,
        "page": 1,
        "per_page": max_contacts * 2,  # Get more to account for filtering
        "reveal_personal_emails": True
    }
    
    # Apply filters based on type
    if filter_type == "managers":
        payload["person_titles"] = ["manager", "head", "lead", "supervisor", "coordinator"]
    elif filter_type == "executives":
        payload["person_seniorities"] = ["c_suite", "vp", "owner", "founder"]
        payload["person_titles"] = [
            "chief", "president", "vice president", "CEO", "CFO", "CTO", 
            "CMO", "COO", "founder", "owner", "partner", "director"
        ]
    
    try:
        app.logger.info(f"Apollo search payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload)
        
        app.logger.info(f"Apollo response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            app.logger.info(f"Apollo response: Found {len(data.get('people', []))} people")
            
            apollo_contacts = data.get('people', [])
            
            valid_contacts = []
            contacts_processed = 0
            
            for person in apollo_contacts:
                if contacts_processed >= max_contacts:
                    break
                    
                # Skip if no basic info
                if not person.get('first_name') or not person.get('last_name'):
                    app.logger.debug(f"Skipping contact without required fields: {person.get('id')}")
                    continue
                
                email = person.get('email')
                person_id = person.get('id')
                
                # For contacts without email, we'll still add them
                # For locked emails, we'll keep them as None instead of the locked placeholder
                if email and "email_not_unlocked@" in email:
                    app.logger.info(f"Contact {person.get('first_name')} {person.get('last_name')} has locked email, will create without email")
                    email = None
                
                organization = person.get('organization', {}) or {}
                
                # Check if department field would exceed 50 characters
                departments = person.get('departments', [])
                if departments:
                    department_text = ', '.join(departments)
                    if len(department_text) > 50:
                        app.logger.warning(f"Skipping contact {person.get('first_name')} {person.get('last_name')} - Department exceeds 50 chars: {len(department_text)}")
                        continue
                
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
                    "departments": departments,
                    "city": person.get('city'),
                    "state": person.get('state'),
                    "country": person.get('country'),
                    "apollo_person_url": f"https://app.apollo.io/#/people/{person.get('id')}" if person.get('id') else None
                }
                
                valid_contacts.append(contact_data)
                contacts_processed += 1
            
            app.logger.info(f"Successfully processed {len(valid_contacts)} contacts with revealed emails")
            return valid_contacts
            
        elif response.status_code == 429:
            app.logger.warning(f"Apollo API rate limit exceeded")
            return []
        else:
            app.logger.error(f"Apollo API error: {response.status_code}")
            app.logger.error(f"Apollo error response: {response.text}")
            return []
            
    except Exception as e:
        app.logger.error(f"Exception searching Apollo contacts: {e}")
        return []

def verificar_contacto_existe_zoho(access_token, email, account_id, first_name=None, last_name=None):
    """Check if contact already exists in Zoho."""
    # If no email, check by name and company
    if not email:
        if not first_name or not last_name:
            return False
            
        url = f"{ZOHO_DOMAIN}/crm/v2/Contacts/search"
        headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
        
        # Search by name and company
        params = {
            'criteria': f'((First_Name:equals:{first_name}) and (Last_Name:equals:{last_name}) and (Account_Name.id:equals:{account_id}))',
            'fields': 'id,First_Name,Last_Name,Account_Name'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                contacts = data.get('data', [])
                
                if contacts:
                    app.logger.info(f"Contact {first_name} {last_name} already exists in company")
                    return True
                    
        except Exception as e:
            app.logger.error(f"Error checking existing contact by name: {e}")
        
        return False
    
    # Original email check
    url = f"{ZOHO_DOMAIN}/crm/v2/Contacts/search"
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
                return True
                
        elif response.status_code == 204:
            return False
            
    except Exception as e:
        app.logger.error(f"Error checking existing contact: {e}")
    
    return False

def verificar_empresa_tiene_contactos(access_token, company_id):
    """Check if a company has any contacts in Zoho."""
    url = f"{ZOHO_DOMAIN}/crm/v2/Contacts/search"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    params = {
        'criteria': f'Account_Name.id:equals:{company_id}',
        'page': 1,
        'per_page': 1
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('data', [])
            contact_count = data.get('info', {}).get('count', len(contacts))
            
            if contacts:
                app.logger.info(f"Company {company_id} has {contact_count} contacts")
                return True, contact_count
                
        elif response.status_code == 204:
            app.logger.info(f"Company {company_id} has no contacts")
            return False, 0
            
    except Exception as e:
        app.logger.error(f"Error checking company contacts: {e}")
        
    return False, 0

def crear_contacto_zoho(access_token, contact_data, account_id):
    """Create contact in Zoho CRM."""
    url = f"{ZOHO_DOMAIN}/crm/v2/Contacts"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Handle Department field - should already be validated in buscar_contactos_apollo
    department = None
    if contact_data.get('departments'):
        department = ', '.join(contact_data.get('departments', []))
    
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
            "Department": department,
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
            return contact_id
        else:
            app.logger.error(f"Error creating contact: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        app.logger.error(f"Exception creating contact: {e}")
        return None

def actualizar_apollo_contact_field(access_token, company_id, has_no_apollo_contacts):
    """Update Apollo_Contact field in Zoho to mark companies with no Apollo contacts."""
    url = f"{ZOHO_DOMAIN}/crm/v2/Accounts/{company_id}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Set Apollo_Contact to true if company has NO contacts in Apollo
    # Zoho expects boolean as string "true" or "false" for picklist fields
    data = {
        "data": [{
            "Apollo_Contact": "true" if has_no_apollo_contacts else "false"
        }]
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            app.logger.info(f"Successfully updated Apollo_Contact field for company {company_id} to {'true' if has_no_apollo_contacts else 'false'}")
            result = response.json()
            app.logger.debug(f"Update response: {result}")
            return True
        else:
            app.logger.error(f"Failed to update Apollo_Contact field: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        app.logger.error(f"Error updating Apollo_Contact field: {e}")
        return False

def verificar_apollo_contact_field(access_token, company_id):
    """Check if company is marked as having no Apollo contacts."""
    url = f"{ZOHO_DOMAIN}/crm/v2/Accounts/{company_id}"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    params = {'fields': 'Apollo_Contact'}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            company_data = data.get('data', [{}])[0]
            apollo_contact = company_data.get('Apollo_Contact', 'false')
            
            # If Apollo_Contact is "true", it means NO contacts in Apollo
            # Handle both boolean and string values
            if isinstance(apollo_contact, bool):
                return apollo_contact
            else:
                return str(apollo_contact).lower() == 'true'
            
    except Exception as e:
        app.logger.error(f"Error checking Apollo_Contact field: {e}")
        
    return False

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

@app.route('/enrich_contacts', methods=['POST'])
@require_api_key
def enrich_contacts():
    """
    Enrich a Zoho company with contacts from Apollo.
    
    Expected JSON payload:
    {
        "company_id": "zoho_company_id",
        "company_name": "Company Name",
        "company_website": "https://example.com",
        "max_contacts": 10,
        "filter_type": "all" | "managers" | "executives",
        "skip_duplicates": true,
        "force_apollo": false
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
        force_apollo = data.get('force_apollo', False)
        
        app.logger.info(f"Enriching company: {company_name} (ID: {company_id})")
        
        # Extract domain from website
        domain = obtener_dominio_desde_url(company_website)
        if not domain:
            return jsonify({'error': 'Could not extract domain from website URL'}), 400
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # First check if company already has contacts in Zoho
        has_contacts, contact_count = verificar_empresa_tiene_contactos(access_token, company_id)
        
        if has_contacts and not force_apollo:
            return jsonify({
                'success': True,
                'message': f'Company already has {contact_count} contacts in Zoho. Skipping Apollo search to save credits.',
                'company': {
                    'id': company_id,
                    'name': company_name,
                    'domain': domain
                },
                'summary': {
                    'existing_contacts': contact_count,
                    'contacts_found': 0,
                    'contacts_created': 0,
                    'apollo_credits_saved': True
                },
                'timestamp': datetime.now().isoformat()
            })
        
        # Check if company is marked as having no Apollo contacts
        if verificar_apollo_contact_field(access_token, company_id) and not force_apollo:
            return jsonify({
                'success': True,
                'message': 'Company is marked as having no contacts in Apollo. Skipping search to save API calls.',
                'company': {
                    'id': company_id,
                    'name': company_name,
                    'domain': domain
                },
                'summary': {
                    'apollo_no_contacts': True,
                    'contacts_found': 0,
                    'contacts_created': 0,
                    'api_calls_saved': True
                },
                'timestamp': datetime.now().isoformat()
            })
        
        # Only search Apollo if company has no contacts and not marked as Apollo empty
        app.logger.info(f"Company has no contacts. Searching Apollo for domain: {domain}")
        contacts = buscar_contactos_apollo(domain, max_contacts, filter_type)
        
        if not contacts:
            # Mark company as having no Apollo contacts
            app.logger.info(f"No contacts found for company {company_id}. Marking Apollo_Contact as true.")
            update_result = actualizar_apollo_contact_field(access_token, company_id, True)
            app.logger.info(f"Apollo_Contact field update result: {update_result}")
            
            return jsonify({
                'success': True,
                'message': 'No contacts found for this domain in Apollo. Company marked to skip future searches.',
                'domain': domain,
                'contacts_found': 0,
                'contacts_created': 0,
                'apollo_marked': True,
                'timestamp': datetime.now().isoformat()
            })
        
        # Create contacts in Zoho
        created_count = 0
        skipped_count = 0
        errors = []
        
        for contact in contacts:
            try:
                # Check if contact already exists
                if skip_duplicates and verificar_contacto_existe_zoho(
                    access_token, 
                    contact.get('email'), 
                    company_id,
                    contact.get('first_name'),
                    contact.get('last_name')
                ):
                    skipped_count += 1
                    app.logger.info(f"Skipped duplicate contact: {contact.get('first_name')} {contact.get('last_name')}")
                    continue
                
                # Create contact
                contact_id = crear_contacto_zoho(access_token, contact, company_id)
                if contact_id:
                    created_count += 1
                else:
                    errors.append(f"Failed to create contact: {contact.get('first_name')} {contact.get('last_name')}")
                    
            except Exception as e:
                error_msg = f"Error processing contact {contact.get('first_name', '')} {contact.get('last_name', '')}: {str(e)}"
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
        app.logger.error(f"Error in enrich_contacts: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def obtener_empresas_sin_contactos(access_token, limit=None):
    """Get companies that don't have any contacts."""
    empresas_sin_contactos = []
    page = 1
    per_page = 200
    
    while True:
        # Get companies
        url = f"{ZOHO_DOMAIN}/crm/v2/Accounts"
        headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
        params = {
            'page': page,
            'per_page': per_page,
            'fields': 'id,Account_Name,Website,Apollo_Contact'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                companies = data.get('data', [])
                
                if not companies:
                    break
                
                # Check each company for contacts
                for company in companies:
                    company_id = company.get('id')
                    company_name = company.get('Account_Name', 'Unknown')
                    website = company.get('Website', '')
                    apollo_contact = company.get('Apollo_Contact', 'false')
                    
                    # Skip if company is marked as having no Apollo contacts
                    # Handle both boolean and string values
                    apollo_has_no_contacts = (apollo_contact == 'true' or apollo_contact == True or str(apollo_contact).lower() == 'true')
                    if apollo_has_no_contacts:
                        app.logger.debug(f"Skipping company {company_name} - marked as no Apollo contacts")
                        continue
                    
                    # Check if company has contacts
                    contacts_url = f"{ZOHO_DOMAIN}/crm/v2/Contacts/search"
                    contacts_params = {
                        'criteria': f'Account_Name.id:equals:{company_id}',
                        'page': 1,
                        'per_page': 1
                    }
                    
                    contacts_response = requests.get(contacts_url, headers=headers, params=contacts_params)
                    
                    # If 204 (no content) or no data, company has no contacts
                    if contacts_response.status_code == 204 or (
                        contacts_response.status_code == 200 and 
                        len(contacts_response.json().get('data', [])) == 0
                    ):
                        empresas_sin_contactos.append({
                            'id': company_id,
                            'name': company_name,
                            'website': website,
                            'apollo_contact': apollo_contact
                        })
                        
                        if limit and len(empresas_sin_contactos) >= limit:
                            return empresas_sin_contactos
                
                # Check if there are more pages
                info = data.get('info', {})
                if not info.get('more_records', False):
                    break
                    
                page += 1
                
            else:
                app.logger.error(f"Error getting companies: {response.status_code}")
                break
                
        except Exception as e:
            app.logger.error(f"Exception getting companies: {e}")
            break
    
    return empresas_sin_contactos

@app.route('/enrich_companies_without_contacts', methods=['POST'])
@require_api_key
def enrich_companies_without_contacts():
    """
    Enrich all companies that don't have contacts.
    
    Expected JSON payload:
    {
        "max_companies": 10,  // Optional: omit or set to 0 to process ALL companies
        "contacts_per_company": 5,
        "filter_type": "managers",
        "dry_run": false
    }
    """
    try:
        data = request.get_json()
        
        max_companies = data.get('max_companies')
        if max_companies is not None:
            max_companies = int(max_companies)
            # If max_companies is 0 or negative, process all companies
            if max_companies <= 0:
                max_companies = None
        else:
            # If max_companies not provided, process all companies
            max_companies = None
            
        contacts_per_company = int(data.get('contacts_per_company', 5))
        filter_type = data.get('filter_type', 'managers')
        dry_run = data.get('dry_run', False)
        
        app.logger.info(f"Starting bulk enrichment: max_companies={'ALL' if max_companies is None else max_companies}, dry_run={dry_run}")
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Get companies without contacts
        app.logger.info("Searching for companies without contacts...")
        companies_without_contacts = obtener_empresas_sin_contactos(access_token, max_companies)
        
        if not companies_without_contacts:
            return jsonify({
                'success': True,
                'message': 'No companies without contacts found',
                'companies_processed': 0,
                'timestamp': datetime.now().isoformat()
            })
        
        app.logger.info(f"Found {len(companies_without_contacts)} companies without contacts")
        
        # Process results
        results = {
            'companies_analyzed': len(companies_without_contacts),
            'companies_enriched': 0,
            'companies_skipped': 0,
            'total_contacts_created': 0,
            'companies': []
        }
        
        # If dry run, just return the companies that would be processed
        if dry_run:
            results['dry_run'] = True
            results['companies_to_process'] = companies_without_contacts
            return jsonify({
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        
        # Process each company
        for company in companies_without_contacts:
            company_result = {
                'id': company['id'],
                'name': company['name'],
                'website': company['website'],
                'status': 'pending'
            }
            
            try:
                # Skip if no website
                if not company['website']:
                    company_result['status'] = 'skipped'
                    company_result['reason'] = 'No website'
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Extract domain
                domain = obtener_dominio_desde_url(company['website'])
                if not domain:
                    company_result['status'] = 'skipped'
                    company_result['reason'] = 'Invalid website domain'
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Search contacts in Apollo
                contacts = buscar_contactos_apollo(domain, contacts_per_company, filter_type)
                
                if not contacts:
                    # Mark company as having no Apollo contacts
                    app.logger.info(f"No contacts found for company {company['name']}. Marking Apollo_Contact as true.")
                    update_result = actualizar_apollo_contact_field(access_token, company['id'], True)
                    app.logger.info(f"Apollo_Contact field update result for {company['name']}: {update_result}")
                    
                    company_result['status'] = 'no_contacts_found'
                    company_result['contacts_found'] = 0
                    company_result['apollo_marked'] = True
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Create contacts in Zoho
                created_count = 0
                for contact in contacts:
                    try:
                        contact_id = crear_contacto_zoho(access_token, contact, company['id'])
                        if contact_id:
                            created_count += 1
                    except Exception as e:
                        app.logger.error(f"Error creating contact: {e}")
                
                company_result['status'] = 'enriched'
                company_result['contacts_found'] = len(contacts)
                company_result['contacts_created'] = created_count
                results['companies_enriched'] += 1
                results['total_contacts_created'] += created_count
                
            except Exception as e:
                company_result['status'] = 'error'
                company_result['error'] = str(e)
                results['companies_skipped'] += 1
                app.logger.error(f"Error processing company {company['name']}: {e}")
            
            results['companies'].append(company_result)
            
            # Small delay between companies to avoid rate limits
            time.sleep(1)
        
        return jsonify({
            'success': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in bulk enrichment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/enrich_companies_chunked', methods=['POST'])
@require_api_key
def enrich_companies_chunked():
    """
    Enrich companies in smaller chunks to avoid timeouts.
    Processes a limited number of companies per request.
    
    Expected JSON payload:
    {
        "chunk_size": 20,        // Number of companies per chunk (default: 20)
        "start_offset": 0,       // Skip this many companies (for pagination)
        "contacts_per_company": 5,
        "filter_type": "managers",
        "session_id": "unique-session-id"  // Optional: for tracking progress
    }
    """
    try:
        data = request.get_json()
        
        chunk_size = int(data.get('chunk_size', 10))  # Reduced to 10 companies to avoid timeout
        start_offset = int(data.get('start_offset', 0))
        contacts_per_company = int(data.get('contacts_per_company', 3))  # Reduced contacts
        filter_type = data.get('filter_type', 'managers')
        session_id = data.get('session_id', datetime.now().isoformat())
        
        app.logger.info(f"Processing chunk: size={chunk_size}, offset={start_offset}, session={session_id}")
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Get companies without contacts (limited to chunk_size)
        all_companies = obtener_empresas_sin_contactos(access_token, None)
        
        # Apply offset and limit
        companies_chunk = all_companies[start_offset:start_offset + chunk_size]
        
        if not companies_chunk:
            return jsonify({
                'success': True,
                'message': 'No more companies to process',
                'session_id': session_id,
                'chunk_info': {
                    'offset': start_offset,
                    'chunk_size': chunk_size,
                    'companies_processed': 0,
                    'total_companies': len(all_companies),
                    'has_more': False
                },
                'timestamp': datetime.now().isoformat()
            })
        
        # Process the chunk
        results = {
            'companies_analyzed': len(companies_chunk),
            'companies_enriched': 0,
            'companies_skipped': 0,
            'total_contacts_created': 0,
            'companies': []
        }
        
        for company in companies_chunk:
            company_result = {
                'id': company['id'],
                'name': company['name'],
                'website': company['website'],
                'status': 'pending'
            }
            
            try:
                # Skip if no website
                if not company['website']:
                    company_result['status'] = 'skipped'
                    company_result['reason'] = 'No website'
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Extract domain
                domain = obtener_dominio_desde_url(company['website'])
                if not domain:
                    company_result['status'] = 'skipped'
                    company_result['reason'] = 'Invalid website domain'
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Search contacts in Apollo
                contacts = buscar_contactos_apollo(domain, contacts_per_company, filter_type)
                
                if not contacts:
                    # Mark company as having no Apollo contacts
                    app.logger.info(f"No contacts found for company {company['name']}. Marking Apollo_Contact as true.")
                    update_result = actualizar_apollo_contact_field(access_token, company['id'], True)
                    app.logger.info(f"Apollo_Contact field update result for {company['name']}: {update_result}")
                    
                    company_result['status'] = 'no_contacts_found'
                    company_result['contacts_found'] = 0
                    company_result['apollo_marked'] = True
                    results['companies_skipped'] += 1
                    results['companies'].append(company_result)
                    continue
                
                # Create contacts in Zoho
                created_count = 0
                for contact in contacts:
                    try:
                        contact_id = crear_contacto_zoho(access_token, contact, company['id'])
                        if contact_id:
                            created_count += 1
                    except Exception as e:
                        app.logger.error(f"Error creating contact: {e}")
                
                company_result['status'] = 'enriched'
                company_result['contacts_found'] = len(contacts)
                company_result['contacts_created'] = created_count
                results['companies_enriched'] += 1
                results['total_contacts_created'] += created_count
                
            except Exception as e:
                company_result['status'] = 'error'
                company_result['error'] = str(e)
                results['companies_skipped'] += 1
                app.logger.error(f"Error processing company {company['name']}: {e}")
            
            results['companies'].append(company_result)
            
            # Small delay between companies to avoid rate limits
            time.sleep(0.5)  # Reduced delay for chunked processing
        
        # Check if there are more companies to process
        has_more = (start_offset + chunk_size) < len(all_companies)
        next_offset = start_offset + chunk_size if has_more else None
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'results': results,
            'chunk_info': {
                'offset': start_offset,
                'chunk_size': chunk_size,
                'companies_processed': len(companies_chunk),
                'total_companies': len(all_companies),
                'has_more': has_more,
                'next_offset': next_offset,
                'progress_percentage': round(((start_offset + len(companies_chunk)) / len(all_companies)) * 100, 2) if all_companies else 100
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in chunked enrichment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'session_id': data.get('session_id'),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/enrich_mini_batch', methods=['POST'])
@require_api_key
def enrich_mini_batch():
    """
    Ultra-lightweight endpoint that processes only 5 companies to avoid timeouts.
    Designed to complete in under 2 minutes.
    
    Expected JSON payload:
    {
        "batch_size": 5,
        "start_offset": 0
    }
    """
    try:
        data = request.get_json() or {}
        
        batch_size = min(int(data.get('batch_size', 5)), 10)  # Max 10 companies
        start_offset = int(data.get('start_offset', 0))
        
        app.logger.info(f"Mini batch processing: size={batch_size}, offset={start_offset}")
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Get limited companies without contacts
        all_companies = obtener_empresas_sin_contactos(access_token, start_offset + batch_size)
        
        # Get only the specific batch
        companies_batch = all_companies[start_offset:start_offset + batch_size]
        
        if not companies_batch:
            return jsonify({
                'success': True,
                'message': 'No companies to process',
                'batch_info': {
                    'offset': start_offset,
                    'batch_size': batch_size,
                    'companies_processed': 0,
                    'completed': True
                }
            })
        
        # Quick processing
        results = {
            'companies_processed': 0,
            'companies_enriched': 0,
            'contacts_created': 0
        }
        
        for company in companies_batch:
            if not company.get('website'):
                continue
                
            domain = obtener_dominio_desde_url(company['website'])
            if not domain:
                continue
            
            # Search only 2 contacts per company for speed
            contacts = buscar_contactos_apollo(domain, 2, 'managers')
            
            if not contacts:
                actualizar_apollo_contact_field(access_token, company['id'], True)
            else:
                for contact in contacts[:2]:  # Max 2 contacts
                    try:
                        crear_contacto_zoho(access_token, contact, company['id'])
                        results['contacts_created'] += 1
                    except:
                        pass
                results['companies_enriched'] += 1
            
            results['companies_processed'] += 1
            
            # Minimal delay
            time.sleep(0.2)
        
        # Calculate if there are more companies
        has_more = len(all_companies) > (start_offset + batch_size)
        
        return jsonify({
            'success': True,
            'results': results,
            'batch_info': {
                'offset': start_offset,
                'batch_size': batch_size,
                'next_offset': start_offset + batch_size if has_more else None,
                'has_more': has_more,
                'completed': not has_more
            },
            'processing_time': f"{results['companies_processed'] * 2} seconds estimated"
        })
        
    except Exception as e:
        app.logger.error(f"Error in mini batch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/analyze_companies', methods=['GET'])
@require_api_key
def analyze_companies():
    """
    Analyze companies to see which ones have contacts and which don't.
    
    Query parameters:
    - limit: Maximum number of companies to analyze (default: 100)
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        app.logger.info(f"Analyzing companies, limit={limit}")
        
        # Get Zoho access token
        access_token = get_access_token()
        
        # Get all companies
        url = f"{ZOHO_DOMAIN}/crm/v2/Accounts"
        headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
        params = {
            'page': 1,
            'per_page': min(limit, 200),
            'fields': 'id,Account_Name,Website,Apollo_Contact'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Error getting companies: {response.status_code}")
        
        companies = response.json().get('data', [])
        
        # Analyze each company
        analysis = {
            'total_companies': len(companies),
            'companies_with_contacts': 0,
            'companies_without_contacts': 0,
            'companies_without_website': 0,
            'companies_marked_no_apollo': 0,
            'details': {
                'with_contacts': [],
                'without_contacts': [],
                'without_website': [],
                'marked_no_apollo': []
            }
        }
        
        for company in companies:
            company_id = company.get('id')
            company_name = company.get('Account_Name', 'Unknown')
            website = company.get('Website', '')
            apollo_contact = company.get('Apollo_Contact', 'false')
            
            # Handle both boolean and string values
            apollo_has_no_contacts = (apollo_contact == 'true' or apollo_contact == True or str(apollo_contact).lower() == 'true')
            
            company_info = {
                'id': company_id,
                'name': company_name,
                'website': website,
                'apollo_contact_marked': apollo_has_no_contacts
            }
            
            # Check if marked as no Apollo contacts
            if apollo_has_no_contacts:
                analysis['companies_marked_no_apollo'] += 1
                analysis['details']['marked_no_apollo'].append(company_info)
            
            # Check if company has website
            if not website:
                analysis['companies_without_website'] += 1
                analysis['details']['without_website'].append(company_info)
                continue
            
            # Check if company has contacts
            contacts_url = f"{ZOHO_DOMAIN}/crm/v2/Contacts/search"
            contacts_params = {
                'criteria': f'Account_Name.id:equals:{company_id}',
                'page': 1,
                'per_page': 1
            }
            
            contacts_response = requests.get(contacts_url, headers=headers, params=contacts_params)
            
            if contacts_response.status_code == 204 or (
                contacts_response.status_code == 200 and 
                len(contacts_response.json().get('data', [])) == 0
            ):
                analysis['companies_without_contacts'] += 1
                analysis['details']['without_contacts'].append(company_info)
            else:
                # Get contact count
                if contacts_response.status_code == 200:
                    # Get total count by checking info
                    total_contacts = contacts_response.json().get('info', {}).get('count', 1)
                    company_info['contact_count'] = total_contacts
                
                analysis['companies_with_contacts'] += 1
                analysis['details']['with_contacts'].append(company_info)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in analyze_companies: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # For development only
    app.run(debug=True, host='0.0.0.0', port=5000)