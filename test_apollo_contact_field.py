#!/usr/bin/env python3
"""Test Apollo_Contact field update functionality"""

import requests
import json

# API configuration
API_KEY = "FL8jC4reI_Bg1fY_9x7YRXpg8sfbwmby7I7iJ_7QBIKpDTtWgp8SOs6NUGhA_qIX"
API_URL = "http://localhost:5000"  # Change to production URL if needed

def test_enrich_company(company_id, company_name, company_website):
    """Test enriching a single company"""
    print(f"\nTesting company enrichment for: {company_name}")
    print("-" * 50)
    
    url = f"{API_URL}/enrich_contacts"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "company_id": company_id,
        "company_name": company_name,
        "company_website": company_website,
        "max_contacts": 3,
        "filter_type": "managers"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Check if company was marked as having no Apollo contacts
            if data.get('apollo_marked'):
                print("\n✓ Company was marked with Apollo_Contact = true")
            elif data.get('summary', {}).get('apollo_no_contacts'):
                print("\n✓ Company already marked with Apollo_Contact = true")
            else:
                print(f"\nContacts found: {data.get('summary', {}).get('contacts_found', 0)}")
                print(f"Contacts created: {data.get('summary', {}).get('contacts_created', 0)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

def test_analyze_companies():
    """Test analyze companies endpoint"""
    print("\nAnalyzing companies...")
    print("-" * 50)
    
    url = f"{API_URL}/analyze_companies"
    headers = {
        "X-API-Key": API_KEY
    }
    params = {"limit": 10}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            analysis = data.get('analysis', {})
            
            print(f"Total companies: {analysis.get('total_companies')}")
            print(f"Companies with contacts: {analysis.get('companies_with_contacts')}")
            print(f"Companies without contacts: {analysis.get('companies_without_contacts')}")
            print(f"Companies marked no Apollo: {analysis.get('companies_marked_no_apollo')}")
            
            # Show companies marked with no Apollo contacts
            marked_companies = analysis.get('details', {}).get('marked_no_apollo', [])
            if marked_companies:
                print(f"\nCompanies marked with Apollo_Contact = true:")
                for company in marked_companies[:5]:
                    print(f"  - {company['name']} (ID: {company['id']})")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("Apollo_Contact Field Test")
    print("=" * 70)
    
    # First analyze companies
    test_analyze_companies()
    
    # Test with a fake company that likely has no Apollo contacts
    print("\n" + "=" * 70)
    test_enrich_company(
        "test_company_id_123",
        "Test Company XYZ",
        "https://www.testcompanyxyz12345.com"
    )
    
    print("\nNote: Run this test locally with the API running to see actual results.")