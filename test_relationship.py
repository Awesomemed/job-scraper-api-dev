#!/usr/bin/env python3
"""
Script para probar la relación entre Jobs y Accounts en Zoho CRM
"""

import requests
import json
import os
from datetime import datetime

# Configuración
API_KEY = 'your-secure-api-key-here'  # Cambiar por tu API key real
BASE_URL = 'https://awesometesting.info/api-zoho'

def test_create_job_with_company():
    """
    Prueba crear un job con una empresa para verificar la relación
    """
    print("=== Probando creación de Job con relación a Account ===\n")
    
    # Headers para la API
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Datos de prueba mínimos
    test_data = {
        "search_term": "Test Relationship",
        "location": "Test City, USA",
        "results_wanted": 1,
        "hours_old": 24,
        "country": "USA"
    }
    
    print("1. Enviando solicitud de prueba...")
    print(f"   URL: POST {BASE_URL}/scrape")
    print(f"   Datos: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/scrape",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        print(f"\n2. Respuesta recibida:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Summary:")
            summary = result.get('summary', {})
            for key, value in summary.items():
                print(f"     - {key}: {value}")
                
            # Verificar si se crearon empresas y jobs
            if summary.get('new_companies_created', 0) > 0:
                print("\n✅ Se crearon empresas nuevas")
            if summary.get('jobs_created', 0) > 0:
                print("✅ Se crearon jobs")
                print("\n⚠️  IMPORTANTE: Verifica en Zoho CRM que:")
                print("   1. El job aparece en el módulo Jobs")
                print("   2. El job tiene el campo 'Account' o 'Related_company' lleno")
                print("   3. Al abrir el job, puedes ver la empresa relacionada")
            else:
                print("\n⚠️  No se crearon jobs. Puede que no haya resultados o ya existan.")
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   Error en la solicitud: {e}")

def test_direct_zoho_api():
    """
    Prueba directa con la API de Zoho para verificar el formato correcto
    """
    print("\n\n=== Ejemplo de formato correcto para Zoho CRM API ===\n")
    
    print("Para crear un Job con relación a Account, el JSON debe ser:")
    print(json.dumps({
        "data": [{
            "Name": "Título del trabajo",
            "Account": "ID_DE_LA_EMPRESA",  # Opción 1: Solo el ID
            # O alternativamente:
            # "Account": {"id": "ID_DE_LA_EMPRESA"},  # Opción 2: Como objeto
            "Related_company": {
                "id": "ID_DE_LA_EMPRESA"
            },
            "Location": "Ciudad, Estado",
            "Description": "Descripción del trabajo"
        }]
    }, indent=2))
    
    print("\n\nNOTA: En Zoho CRM, los campos de lookup pueden aceptar:")
    print("1. Solo el ID como string: 'Account': '123456789'")
    print("2. Como objeto con id: 'Account': {'id': '123456789'}")
    print("\nNuestro código ahora usa la opción 1 para Account y opción 2 para Related_company")

if __name__ == "__main__":
    print("Este script probará la relación entre Jobs y Accounts\n")
    
    # Ejecutar pruebas
    test_create_job_with_company()
    test_direct_zoho_api()
    
    print("\n\n=== Pasos para verificar manualmente ===")
    print("1. Ingresa a Zoho CRM")
    print("2. Ve al módulo 'Jobs'")
    print("3. Busca el job más reciente")
    print("4. Verifica que tenga una empresa asociada en el campo 'Account' o 'Related Company'")
    print("5. Si no aparece la relación, revisa:")
    print("   - Los nombres exactos de los campos en tu configuración de Zoho")
    print("   - Los permisos del API token para modificar relaciones")
    print("   - El log de la API en job-scraper-api/logs/api.log")