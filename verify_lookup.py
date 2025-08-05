#!/usr/bin/env python3
"""
Script para verificar que el campo Lookup_1 se está llenando correctamente
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

def check_lookup_field(access_token):
    """Verificar el campo Lookup_1 en Jobs recientes"""
    print("=== Verificando campo Lookup_1 en Jobs ===\n")
    
    # Obtener los últimos 5 jobs
    url = f"{ZOHO_DOMAIN}/crm/v2/Jobs?per_page=5&sort_by=Created_Time&sort_order=desc"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        jobs = response.json().get('data', [])
        
        print(f"Analizando {len(jobs)} jobs más recientes:\n")
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. Job: {job.get('Name', 'Sin nombre')}")
            print(f"   ID: {job.get('id')}")
            print(f"   Creado: {job.get('Created_Time', 'Desconocido')}")
            
            # Verificar campos de relación con empresa
            account = job.get('Account')
            related_company = job.get('Related_company')
            lookup_1 = job.get('Lookup_1')
            
            print(f"   Campos de relación con empresa:")
            print(f"     - Account: {account}")
            print(f"     - Related_company: {related_company}")
            print(f"     - Lookup_1: {lookup_1}")
            
            # Verificar si todos apuntan a la misma empresa
            if lookup_1:
                print(f"   ✅ Lookup_1 está lleno")
            else:
                print(f"   ❌ Lookup_1 está vacío")
            
            print()
    else:
        print(f"Error obteniendo jobs: {response.status_code}")
        print(f"Respuesta: {response.text}")

def test_create_job_with_lookup(access_token):
    """Crear un job de prueba con Lookup_1"""
    print("\n=== Creando Job de prueba con Lookup_1 ===\n")
    
    # Primero obtener una empresa
    accounts_url = f"{ZOHO_DOMAIN}/crm/v2/Accounts?per_page=1"
    response = requests.get(accounts_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
    
    if response.status_code == 200 and response.json().get('data'):
        account = response.json()['data'][0]
        company_id = account['id']
        company_name = account.get('Account_Name', 'Unknown')
        print(f"Usando empresa: {company_name} (ID: {company_id})")
        
        # Crear job con Lookup_1
        jobs_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs"
        headers = {
            'Authorization': f'Zoho-oauthtoken {access_token}',
            'Content-Type': 'application/json'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        job_data = {
            "data": [{
                "Name": f"Test Job Lookup_1 - {timestamp}",
                "ID_Indeed": f"test_{timestamp}",
                "Location": "Test Location",
                "Account": company_id,
                "Related_company": {"id": company_id},
                "Lookup_1": {"id": company_id}
            }]
        }
        
        print("\nEnviando datos:")
        print(json.dumps(job_data, indent=2))
        
        response = requests.post(jobs_url, headers=headers, json=job_data)
        
        if response.status_code == 201:
            job_id = response.json()['data'][0]['details']['id']
            print(f"\n✅ Job creado exitosamente con ID: {job_id}")
            
            # Verificar que se guardó correctamente
            verify_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs/{job_id}"
            verify_response = requests.get(verify_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
            
            if verify_response.status_code == 200:
                created_job = verify_response.json()['data'][0]
                print(f"\nVerificando job creado:")
                print(f"  - Account: {created_job.get('Account')}")
                print(f"  - Related_company: {created_job.get('Related_company')}")
                print(f"  - Lookup_1: {created_job.get('Lookup_1')}")
                
                if created_job.get('Lookup_1'):
                    print(f"\n✅ Lookup_1 se guardó correctamente!")
                else:
                    print(f"\n❌ Lookup_1 no se guardó")
        else:
            print(f"\n❌ Error creando job: {response.status_code}")
            print(f"Respuesta: {response.text}")
    else:
        print("No se encontraron empresas para la prueba")

def main():
    try:
        # Obtener token
        print("Obteniendo token de acceso...")
        access_token = get_access_token()
        print("✅ Token obtenido\n")
        
        # Verificar jobs existentes
        check_lookup_field(access_token)
        
        # Preguntar si crear job de prueba
        print("\n¿Deseas crear un job de prueba? (s/n): ", end="")
        try:
            respuesta = input().strip().lower()
            if respuesta == 's':
                test_create_job_with_lookup(access_token)
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()