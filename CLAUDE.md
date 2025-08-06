# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based REST API that scrapes job listings from Indeed and enriches company data using Apollo.io, storing everything in Zoho CRM. The API supports both synchronous and background job processing, with multiple deployment options (Vercel serverless or traditional server).

## Key Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python run_dev.py

# Run production server locally
./run_production.sh
```

### Testing
```bash
# Test basic API functionality
python test_api.py

# Test production environment
python test_production.py

# Test Apollo contact field functionality
python test_apollo_contact_field.py

# Test all response formats
python test_all_formats.py
```

### Deployment

For Vercel deployment:
1. Push to repository (auto-deploys with vercel.json)
2. Set environment variables in Vercel dashboard

For traditional deployment:
```bash
# Use gunicorn with extended timeout (30 minutes)
gunicorn -c gunicorn_config.py app:app
```

## Architecture Overview

### Core Components

1. **app.py** - Main Flask application containing all endpoints and business logic
   - Job scraping from Indeed using jobspy library
   - Company enrichment via Apollo.io API
   - Zoho CRM integration for data storage
   - Background job processing with threading
   - API key authentication middleware

2. **config.py** - Environment-based configuration
   - Manages API keys and secrets from environment variables
   - Validates required configuration on startup
   - Provides defaults for scraping parameters

3. **contacts_api.py** - Separate Flask app for contact enrichment
   - Independent deployment option
   - Focuses on Apollo.io contact discovery
   - Bulk enrichment capabilities

### External Service Integration

**Apollo.io Integration:**
- Company enrichment: `enriquecer_empresa_apollo()` 
- Contact search: `buscar_contactos_apollo()`
- Smart caching to minimize API calls
- Marks companies with no contacts to avoid repeat searches

**Zoho CRM Integration:**
- OAuth 2.0 with refresh token: `get_access_token()`
- Company (Account) management: `buscar_empresa_en_zoho()`, `crear_empresa_en_zoho()`
- Job creation with company relationships: `crear_trabajo_en_zoho()`
- Contact management: `crear_contacto_zoho()`, `verificar_contacto_existe_zoho()`
- Junction table support for many-to-many relationships

### Key Workflows

**Job Scraping Flow:**
1. `/scrape` endpoint receives search parameters
2. Queries Indeed via jobspy library
3. For each job found:
   - Checks if company exists in Zoho (with caching)
   - Creates company if needed (with Apollo enrichment)
   - Creates job record linked to company
   - Handles duplicates via Indeed ID checking

**Contact Enrichment Flow:**
1. `/enrich_contacts` receives company ID and website
2. Checks if company already has contacts (saves API calls)
3. Checks Apollo_Contact field (marks companies with no Apollo data)
4. Searches Apollo.io for contacts if needed
5. Creates contacts in Zoho, avoiding duplicates

### Performance Considerations

- **Chunked Processing**: `/enrich_companies_chunked` and `/enrich_mini_batch` for handling large datasets without timeouts
- **Background Jobs**: Thread-based processing for long-running scraping tasks
- **Caching**: In-memory company cache during batch operations
- **Rate Limiting**: Built-in delays between API calls (0.5-1.5 seconds)
- **Timeout Configuration**: Gunicorn configured for 30-minute timeout for large jobs

### Environment Variables

Required in `.env` file:
```
SECRET_KEY=<flask-secret-key>
API_KEY=<api-authentication-key>
APOLLO_API_KEY=<apollo-api-key>
ZOHO_CLIENT_ID=<zoho-oauth-client-id>
ZOHO_CLIENT_SECRET=<zoho-oauth-client-secret>
ZOHO_REFRESH_TOKEN=<zoho-oauth-refresh-token>
```

### API Authentication

All endpoints except `/health` require API key authentication:
- Header: `X-API-Key: <your-api-key>`
- Alternative: `?api_key=<your-api-key>` query parameter

### Vercel Deployment Notes

When deploying to Vercel:
1. The current `vercel.json` points to `app.py` directly
2. For proper serverless deployment, need to create `/api` directory structure
3. Convert Flask app to Vercel's serverless function format
4. Environment variables must be set in Vercel dashboard
5. Consider timeout limits (Vercel has shorter timeouts than traditional hosting)

### Zoho CRM Field Mapping

Important custom fields in Zoho:
- **Accounts**: Apollo_Contact (boolean - true means NO contacts found in Apollo)
- **Jobs**: ID_Indeed, Related_company, Account, Lookup_1
- **Contacts**: Apollo_ID, Apollo_URL, Department (max 50 chars)

### Common Issues and Solutions

1. **Department field errors**: Apollo departments can exceed Zoho's 50-character limit. The code validates this before creating contacts.

2. **Timeout errors**: Use chunked endpoints (`/enrich_companies_chunked`, `/enrich_mini_batch`) for large operations.

3. **Rate limiting**: Built-in delays prevent hitting API limits. Adjust `time.sleep()` values if needed.

4. **Duplicate contacts**: The system checks by email first, then by name+company if no email exists.

5. **Junction table failures**: The Account_X_Job junction is created after job creation. Failures are logged but don't block job creation.