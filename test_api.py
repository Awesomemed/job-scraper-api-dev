#!/usr/bin/env python3
"""
Script para probar la API
"""

import requests
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
BASE_URL = "http://localhost:5000"  # Cambia esto a tu URL de producción
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key-here')

print("=== Probando Job Scraper API ===\n")
print(f"URL Base: {BASE_URL}")
print(f"API Key: {API_KEY[:10]}...")
print("-" * 50)

# Test 1: Health Check (sin autenticación)
print("\n1. Probando Health Check (sin autenticación):")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Test Auth con API Key en header
print("\n2. Probando autenticación con API Key en header:")
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}
try:
    response = requests.get(f"{BASE_URL}/test-auth", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Test Auth sin API Key (debe fallar)
print("\n3. Probando sin API Key (debe fallar):")
try:
    response = requests.get(f"{BASE_URL}/test-auth")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 4: Test Auth con API Key incorrecta (debe fallar)
print("\n4. Probando con API Key incorrecta (debe fallar):")
bad_headers = {
    "X-API-Key": "wrong-api-key",
    "Content-Type": "application/json"
}
try:
    response = requests.get(f"{BASE_URL}/test-auth", headers=bad_headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 5: Scrape endpoint con datos mínimos
print("\n5. Probando endpoint /scrape con datos mínimos:")
scrape_data = {
    "search_term": "Test",
    "location": "Test City",
    "results_wanted": 1,
    "hours_old": 24,
    "country": "USA"
}
try:
    response = requests.post(
        f"{BASE_URL}/scrape", 
        headers=headers,
        json=scrape_data
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 50)
print("CONFIGURACIÓN PARA POSTMAN:")
print("=" * 50)
print("\n1. URL: POST " + BASE_URL + "/scrape")
print("\n2. Headers:")
print("   X-API-Key: " + API_KEY)
print("   Content-Type: application/json")
print("\n3. Body (raw JSON):")
print(json.dumps({
    "search_term": "Call Center",
    "location": "Arizona, USA",
    "results_wanted": 50,
    "hours_old": 1440,
    "country": "USA"
}, indent=2))
print("\n4. Para probar autenticación:")
print("   GET " + BASE_URL + "/test-auth")
print("   Header: X-API-Key: " + API_KEY)