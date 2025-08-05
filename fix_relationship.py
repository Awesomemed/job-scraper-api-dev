#!/usr/bin/env python3
"""
Script para diagnosticar y corregir problemas de relación Jobs-Accounts
"""

import requests
import json
import os

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

def get_job_fields(access_token):
    """Obtener todos los campos del módulo Jobs"""
    url = f"{ZOHO_DOMAIN}/crm/v2/settings/fields?module=Jobs"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        fields = response.json().get('fields', [])
        
        print("=== Campos de tipo Lookup en el módulo Jobs ===\n")
        lookup_fields = []
        
        for field in fields:
            if field.get('data_type') == 'lookup':
                api_name = field.get('api_name')
                field_label = field.get('field_label')
                lookup_module = field.get('lookup', {}).get('module', 'Unknown')
                
                print(f"Campo: {field_label}")
                print(f"  API Name: {api_name}")
                print(f"  Relacionado con: {lookup_module}")
                print(f"  Requerido: {field.get('required', False)}")
                print()
                
                if 'account' in api_name.lower() or 'account' in lookup_module.lower():
                    lookup_fields.append(api_name)
        
        return lookup_fields
    else:
        print(f"Error obteniendo campos: {response.text}")
        return []

def test_create_job_with_formats(access_token, company_id):
    """Probar diferentes formatos para crear la relación"""
    url = f"{ZOHO_DOMAIN}/crm/v2/Jobs"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Diferentes formatos a probar
    test_formats = [
        {
            "name": "Format 1: Account as string ID",
            "data": {
                "data": [{
                    "Name": f"Test Job - Format 1 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Account": company_id
                }]
            }
        },
        {
            "name": "Format 2: Account as object with id",
            "data": {
                "data": [{
                    "Name": f"Test Job - Format 2 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Account": {"id": company_id}
                }]
            }
        },
        {
            "name": "Format 3: Related_company as string",
            "data": {
                "data": [{
                    "Name": f"Test Job - Format 3 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Related_company": company_id
                }]
            }
        },
        {
            "name": "Format 4: Related_company as object",
            "data": {
                "data": [{
                    "Name": f"Test Job - Format 4 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Related_company": {"id": company_id}
                }]
            }
        },
        {
            "name": "Format 5: Both Account and Related_company",
            "data": {
                "data": [{
                    "Name": f"Test Job - Format 5 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "Account": company_id,
                    "Related_company": {"id": company_id}
                }]
            }
        }
    ]
    
    print("\n=== Probando diferentes formatos para establecer la relación ===\n")
    
    for test in test_formats:
        print(f"Probando: {test['name']}")
        print(f"JSON: {json.dumps(test['data'], indent=2)}")
        
        response = requests.post(url, headers=headers, json=test['data'])
        
        if response.status_code == 201:
            result = response.json()
            job_id = result['data'][0]['details']['id']
            print(f"✅ ÉXITO - Job creado con ID: {job_id}")
            
            # Verificar si la relación se estableció
            verify_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs/{job_id}"
            verify_response = requests.get(verify_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
            
            if verify_response.status_code == 200:
                job_data = verify_response.json()['data'][0]
                
                # Buscar campos de Account
                account_fields = ['Account', 'Related_company', 'account', 'related_company']
                for field in account_fields:
                    if field in job_data and job_data[field]:
                        print(f"   ✅ Relación establecida en campo '{field}': {job_data[field]}")
                        return field  # Retornar el campo que funcionó
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            error_data = response.json()
            if 'details' in error_data:
                print(f"   Detalles: {error_data['details']}")
        
        print()
    
    return None

def main():
    print("=== Diagnóstico de Relación Jobs-Accounts ===\n")
    
    try:
        # Obtener token
        print("1. Obteniendo token de acceso...")
        access_token = get_access_token()
        print("✅ Token obtenido\n")
        
        # Obtener campos del módulo Jobs
        print("2. Analizando campos del módulo Jobs...")
        lookup_fields = get_job_fields(access_token)
        
        if lookup_fields:
            print(f"\nCampos encontrados para relación con Accounts: {lookup_fields}")
        
        # Obtener un ID de empresa para pruebas
        print("\n3. Buscando una empresa para pruebas...")
        accounts_url = f"{ZOHO_DOMAIN}/crm/v2/Accounts?per_page=1"
        response = requests.get(accounts_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
        
        if response.status_code == 200 and response.json().get('data'):
            company = response.json()['data'][0]
            company_id = company['id']
            company_name = company.get('Account_Name', 'Unknown')
            print(f"✅ Usando empresa: {company_name} (ID: {company_id})")
            
            # Probar diferentes formatos
            working_field = test_create_job_with_formats(access_token, company_id)
            
            if working_field:
                print(f"\n\n✅ SOLUCIÓN ENCONTRADA ✅")
                print(f"El campo que funciona es: '{working_field}'")
                print(f"\nActualiza tu código para usar:")
                print(f'job_data_dict["data"][0]["{working_field}"] = company_id')
            else:
                print("\n❌ Ningún formato funcionó. Verifica:")
                print("1. Los permisos del token de API")
                print("2. La configuración de campos obligatorios en Zoho")
                print("3. Los nombres exactos de los campos en tu instancia de Zoho")
                
        else:
            print("❌ No se encontraron empresas para pruebas")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    from datetime import datetime
    main()