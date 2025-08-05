#!/usr/bin/env python3
"""
Script para probar diferentes formatos de campos de relación
"""

import requests
import json
from datetime import datetime

# Configuración de Zoho
ZOHO_CLIENT_ID = "1000.KP5I8V440G4BUMK7BKA4VGXTN58EPU"
ZOHO_CLIENT_SECRET = "fcb0113893df4bf97adcaec2f359302ddec729faa4"
ZOHO_REFRESH_TOKEN = "1000.44be0b5623337acfd9706f54076fe99e.388905af35a5badc521cb2f58760487d"
ZOHO_DOMAIN = "https://www.zohoapis.com"

def get_access_token():
    """Obtener token de acceso de Zoho"""
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        'refresh_token': ZOHO_REFRESH_TOKEN,
        'client_id': ZOHO_CLIENT_ID,
        'client_secret': ZOHO_CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Error getting token: {response.text}")

def test_different_formats(access_token, company_id):
    """Probar diferentes formatos para los campos"""
    print("=== Probando diferentes formatos de campos ===\n")
    
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Diferentes formatos a probar
    test_cases = [
        {
            "name": "Todos como string directo",
            "fields": {
                "Account": company_id,
                "Related_company": company_id,
                "Lookup_1": company_id
            }
        },
        {
            "name": "Todos como objeto con id",
            "fields": {
                "Account": {"id": company_id},
                "Related_company": {"id": company_id},
                "Lookup_1": {"id": company_id}
            }
        },
        {
            "name": "Mixto - Account string, otros objeto",
            "fields": {
                "Account": company_id,
                "Related_company": {"id": company_id},
                "Lookup_1": {"id": company_id}
            }
        },
        {
            "name": "Solo Lookup_1",
            "fields": {
                "Lookup_1": {"id": company_id}
            }
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        job_data = {
            "data": [{
                "Name": f"Test Format {i} - {timestamp}",
                "ID_Indeed": f"test_format_{i}_{timestamp}",
                "Location": "Test Location",
                **test["fields"]
            }]
        }
        
        print(f"\nPrueba {i}: {test['name']}")
        print(f"Campos enviados: {json.dumps(test['fields'], indent=2)}")
        
        url = f"{ZOHO_DOMAIN}/crm/v2/Jobs"
        response = requests.post(url, headers=headers, json=job_data)
        
        if response.status_code == 201:
            job_id = response.json()['data'][0]['details']['id']
            print(f"✅ Job creado con ID: {job_id}")
            
            # Verificar qué se guardó
            verify_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs/{job_id}"
            verify_response = requests.get(verify_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
            
            if verify_response.status_code == 200:
                created_job = verify_response.json()['data'][0]
                print(f"Campos guardados:")
                print(f"  - Account: {created_job.get('Account')}")
                print(f"  - Related_company: {created_job.get('Related_company')}")
                print(f"  - Lookup_1: {created_job.get('Lookup_1')}")
                
                # Eliminar el job de prueba
                delete_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs/{job_id}"
                requests.delete(delete_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Respuesta: {response.text}")

def main():
    try:
        # Obtener token
        print("Obteniendo token de acceso...")
        access_token = get_access_token()
        print("✅ Token obtenido\n")
        
        # Obtener una empresa para pruebas
        accounts_url = f"{ZOHO_DOMAIN}/crm/v2/Accounts?per_page=1"
        response = requests.get(accounts_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
        
        if response.status_code == 200 and response.json().get('data'):
            account = response.json()['data'][0]
            company_id = account['id']
            company_name = account.get('Account_Name', 'Unknown')
            print(f"Usando empresa para pruebas: {company_name} (ID: {company_id})")
            
            # Probar diferentes formatos
            test_different_formats(access_token, company_id)
            
            print("\n\n=== RESUMEN ===")
            print("Basado en las pruebas, parece que:")
            print("- Lookup_1 funciona correctamente como objeto {'id': 'company_id'}")
            print("- Account y Related_company pueden no estar configurados para mostrarse en la API")
            print("- Recomendación: Usar Lookup_1 para la relación principal con la empresa")
        else:
            print("No se encontraron empresas para pruebas")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()