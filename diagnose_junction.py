#!/usr/bin/env python3
"""
Script para diagnosticar el módulo de enlace Account_X_Job
"""

import requests
import json
import os
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

def check_module_exists(access_token, module_name):
    """Verificar si un módulo existe"""
    url = f"{ZOHO_DOMAIN}/crm/v2/{module_name}"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    response = requests.get(url, headers=headers)
    return response.status_code != 400

def get_junction_module_fields(access_token, module_name):
    """Obtener campos del módulo de enlace"""
    url = f"{ZOHO_DOMAIN}/crm/v2/settings/fields?module={module_name}"
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    
    print(f"\n=== Analizando módulo: {module_name} ===")
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        fields_data = response.json()
        fields = fields_data.get('fields', [])
        
        print(f"Total de campos encontrados: {len(fields)}")
        
        # Buscar campos de tipo lookup
        lookup_fields = {}
        required_fields = []
        
        for field in fields:
            field_name = field.get('api_name', '')
            field_type = field.get('data_type', '')
            field_label = field.get('field_label', '')
            is_required = field.get('required', False)
            
            if is_required and field_name != 'id':
                required_fields.append(field_name)
            
            if field_type == 'lookup':
                lookup_info = field.get('lookup', {})
                related_module = lookup_info.get('module', 'Unknown')
                
                lookup_fields[field_name] = {
                    'label': field_label,
                    'related_module': related_module,
                    'required': is_required
                }
        
        print(f"\nCampos obligatorios: {required_fields}")
        print(f"\nCampos de relación (lookup):")
        for field_name, info in lookup_fields.items():
            print(f"  - {field_name}:")
            print(f"    Label: {info['label']}")
            print(f"    Módulo relacionado: {info['related_module']}")
            print(f"    Requerido: {info['required']}")
        
        return lookup_fields
    else:
        print(f"Error obteniendo campos: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return {}

def test_junction_creation(access_token, module_name, job_id, account_id):
    """Probar la creación de registros en el módulo de enlace"""
    url = f"{ZOHO_DOMAIN}/crm/v2/{module_name}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n=== Probando creación en {module_name} ===")
    print(f"Job ID: {job_id}")
    print(f"Account ID: {account_id}")
    
    # Diferentes formatos a probar
    test_formats = [
        {
            "name": "Formato 1: Jobs y Accounts (plural)",
            "data": {
                "data": [{
                    "Jobs": {"id": job_id},
                    "Accounts": {"id": account_id}
                }]
            }
        },
        {
            "name": "Formato 2: Job y Account (singular)",
            "data": {
                "data": [{
                    "Job": {"id": job_id},
                    "Account": {"id": account_id}
                }]
            }
        },
        {
            "name": "Formato 3: Related_Job y Related_Account",
            "data": {
                "data": [{
                    "Related_Job": {"id": job_id},
                    "Related_Account": {"id": account_id}
                }]
            }
        },
        {
            "name": "Formato 4: Job_Id y Account_Id",
            "data": {
                "data": [{
                    "Job_Id": {"id": job_id},
                    "Account_Id": {"id": account_id}
                }]
            }
        },
        {
            "name": "Formato 5: Solo IDs como strings",
            "data": {
                "data": [{
                    "Job": job_id,
                    "Account": account_id
                }]
            }
        }
    ]
    
    for test in test_formats:
        print(f"\nProbando: {test['name']}")
        print(f"JSON: {json.dumps(test['data'], indent=2)}")
        
        response = requests.post(url, headers=headers, json=test['data'])
        
        if response.status_code == 201:
            result = response.json()
            junction_id = result['data'][0]['details']['id']
            print(f"✅ ÉXITO - Registro creado con ID: {junction_id}")
            
            # Guardar el formato exitoso
            with open('working_junction_format.json', 'w') as f:
                json.dump({
                    'module': module_name,
                    'format': test['data'],
                    'description': test['name']
                }, f, indent=2)
            
            return test['data']
        elif response.status_code == 202:
            print(f"⚠️  CÓDIGO 202 (Accepted)")
            try:
                response_data = response.json()
                print(f"   Respuesta completa: {json.dumps(response_data, indent=2)}")
                
                # Intentar con el formato correcto basado en los campos encontrados
                if test == test_formats[-1]:  # Si es el último intento
                    print(f"\n   Probando con campos correctos del módulo...")
                    correct_format = {
                        "data": [{
                            "Related_Job": {"id": job_id},
                            "Related_company": {"id": account_id}
                        }]
                    }
                    print(f"   JSON: {json.dumps(correct_format, indent=2)}")
                    
                    response2 = requests.post(url, headers=headers, json=correct_format)
                    if response2.status_code == 201:
                        print(f"   ✅ ÉXITO con campos correctos!")
                        return correct_format
                    else:
                        print(f"   ❌ También falló: {response2.status_code}")
                        print(f"   Respuesta: {response2.text}")
            except:
                print(f"   Respuesta: {response.text}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            try:
                error_data = response.json()
                if 'details' in error_data:
                    print(f"   Detalles: {error_data['details']}")
                if 'message' in error_data:
                    print(f"   Mensaje: {error_data['message']}")
            except:
                print(f"   Respuesta: {response.text}")
    
    return None

def main():
    print("=== Diagnóstico del Módulo de Enlace Account_X_Job ===\n")
    
    try:
        # Obtener token
        print("1. Obteniendo token de acceso...")
        access_token = get_access_token()
        print("✅ Token obtenido\n")
        
        # Verificar módulos de enlace posibles
        possible_modules = [
            "Account_X_Job",
            "Account_X_Jobs", 
            "Accounts_X_Job",
            "Accounts_X_Jobs",
            "Job_X_Account",
            "Jobs_X_Account",
            "Job_X_Accounts",
            "Jobs_X_Accounts"
        ]
        
        print("2. Buscando módulos de enlace...")
        existing_modules = []
        
        for module in possible_modules:
            if check_module_exists(access_token, module):
                print(f"✅ Módulo encontrado: {module}")
                existing_modules.append(module)
            else:
                print(f"❌ Módulo no existe: {module}")
        
        if not existing_modules:
            print("\n❌ No se encontró ningún módulo de enlace")
            print("Verifica en Zoho CRM Setup > Modules and Fields")
            return
        
        # Analizar cada módulo encontrado
        for module in existing_modules:
            fields = get_junction_module_fields(access_token, module)
        
        # Obtener IDs para prueba
        print("\n3. Obteniendo IDs para prueba...")
        
        # Obtener un Job
        jobs_url = f"{ZOHO_DOMAIN}/crm/v2/Jobs?per_page=1"
        response = requests.get(jobs_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
        
        if response.status_code == 200 and response.json().get('data'):
            job = response.json()['data'][0]
            job_id = job['id']
            job_name = job.get('Name', 'Unknown')
            print(f"✅ Job para prueba: {job_name} (ID: {job_id})")
        else:
            print("❌ No se encontraron Jobs")
            return
        
        # Obtener un Account
        accounts_url = f"{ZOHO_DOMAIN}/crm/v2/Accounts?per_page=1"
        response = requests.get(accounts_url, headers={'Authorization': f'Zoho-oauthtoken {access_token}'})
        
        if response.status_code == 200 and response.json().get('data'):
            account = response.json()['data'][0]
            account_id = account['id']
            account_name = account.get('Account_Name', 'Unknown')
            print(f"✅ Account para prueba: {account_name} (ID: {account_id})")
        else:
            print("❌ No se encontraron Accounts")
            return
        
        # Probar creación en cada módulo encontrado
        for module in existing_modules:
            working_format = test_junction_creation(access_token, module, job_id, account_id)
            
            if working_format:
                print(f"\n\n✅ SOLUCIÓN ENCONTRADA ✅")
                print(f"Módulo que funciona: {module}")
                print(f"Formato que funciona:")
                print(json.dumps(working_format, indent=2))
                print(f"\nActualiza tu código para usar este formato exacto.")
                break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()