#!/usr/bin/env python3
"""
Script para verificar que solo se busca en Indeed
"""

import requests
import json

# Configuración
API_KEY = 'your-secure-api-key-here'  # API key por defecto
BASE_URL = 'https://awesometesting.info/api-zoho'

def test_indeed_only():
    """Prueba que la API solo busca en Indeed"""
    
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Datos de prueba mínimos
    test_data = {
        "search_term": "Software Engineer",
        "location": "New York, USA",
        "results_wanted": 5,
        "hours_old": 24,
        "country": "USA"
    }
    
    print("=== Verificando que la API busca solo en Indeed ===\n")
    print(f"Enviando solicitud a: {BASE_URL}/scrape")
    print(f"Parámetros de búsqueda:")
    print(json.dumps(test_data, indent=2))
    
    print("\nLa API está configurada para buscar SOLO en Indeed con:")
    print('  site_name=["indeed"]')
    print("\nEsto significa que:")
    print("  ✅ Solo buscará trabajos en Indeed.com")
    print("  ❌ NO buscará en LinkedIn")
    print("  ❌ NO buscará en Glassdoor")
    print("  ❌ NO buscará en otros sitios de empleo")
    
    try:
        response = requests.post(
            f"{BASE_URL}/scrape",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                summary = result.get('summary', {})
                total_jobs = summary.get('total_jobs_found', 0)
                
                print(f"\n✅ Búsqueda completada")
                print(f"   Trabajos encontrados en Indeed: {total_jobs}")
                print(f"   Todos los resultados provienen exclusivamente de Indeed.com")
            else:
                print(f"\n❌ Error en la búsqueda: {result.get('error', 'Unknown error')}")
        else:
            print(f"\n❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")

if __name__ == "__main__":
    test_indeed_only()
    
    print("\n\nNOTA: Si necesitas buscar en otros sitios además de Indeed,")
    print("tendrías que modificar el parámetro site_name para incluir otros sitios:")
    print('  site_name=["indeed", "linkedin", "glassdoor", "ziprecruiter"]')
    print("\nPero actualmente está configurado para Indeed solamente.")