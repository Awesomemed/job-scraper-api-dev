#!/usr/bin/env python3
"""
Script para probar la API en producción
"""

import requests
import json
import os

# Configuración de producción
BASE_URL = "https://awesometesting.info/api-zoho"
API_KEY = 'FL8jC4reI_Bg1fY_9x7YRXpg8sfbwmby7I7iJ_7QBIKpDTtWgp8SOs6NUGhA_qIX'

print("=== Probando Job Scraper API en Producción ===\n")
print(f"URL Base: {BASE_URL}")
print(f"API Key: {API_KEY[:10]}...")
print("-" * 50)

# Test 1: Health Check (sin autenticación)
print("\n1. Probando Health Check (sin autenticación):")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Test Auth con API Key
print("\n2. Probando autenticación con API Key:")
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}
try:
    response = requests.get(f"{BASE_URL}/test-auth", headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Verificar el index
print("\n3. Verificando endpoint principal:")
try:
    response = requests.get(BASE_URL, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        try:
            print(f"   Response: {response.json()}")
        except:
            print(f"   Response: {response.text[:200]}...")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 50)
print("CONFIGURACIÓN PARA POSTMAN:")
print("=" * 50)

print("\n1. Para probar autenticación:")
print(f"   GET {BASE_URL}/test-auth")
print(f"   Header: X-API-Key: {API_KEY}")

print("\n2. Para ejecutar scraping:")
print(f"   POST {BASE_URL}/scrape")
print("   Headers:")
print(f"     X-API-Key: {API_KEY}")
print("     Content-Type: application/json")
print("\n   Body (raw JSON):")
print(json.dumps({
    "search_term": "Call Center",
    "location": "Arizona, USA",
    "results_wanted": 10,
    "hours_old": 1440,
    "country": "USA"
}, indent=2))

print("\n" + "=" * 50)
print("EJEMPLO CON CURL:")
print("=" * 50)

print("\n# Test de autenticación:")
print(f'curl -H "X-API-Key: {API_KEY}" {BASE_URL}/test-auth')

print("\n# Ejecutar scraping:")
print(f'''curl -X POST {BASE_URL}/scrape \\
  -H "X-API-Key: {API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{{"search_term":"Call Center","location":"Arizona, USA","results_wanted":10,"hours_old":1440,"country":"USA"}}' ''')

print("\n" + "=" * 50)
print("CONFIGURACIÓN PARA N8N:")
print("=" * 50)

print("\nHTTP Request Node:")
print(f"- Method: POST")
print(f"- URL: {BASE_URL}/scrape")
print("- Authentication: None (usaremos headers)")
print("- Headers:")
print(f"    X-API-Key: {API_KEY}")
print("    Content-Type: application/json")
print("- Body Type: JSON")
print("- Body: (usar el JSON de ejemplo arriba)")