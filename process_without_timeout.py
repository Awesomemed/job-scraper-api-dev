#!/usr/bin/env python3
"""
Script para procesar empresas sin timeout usando mini batches
Procesa 5 empresas a la vez para evitar el error 500
"""

import requests
import time
import json
from datetime import datetime
import sys

# Configuración
API_URL = "https://awesometesting.info/api-zoho"
API_KEY = "FL8jC4reI_Bg1fY_9x7YRXpg8sfbwmby7I7iJ_7QBIKpDTtWgp8SOs6NUGhA_qIX"
BATCH_SIZE = 5  # Solo 5 empresas por request para evitar timeout
DELAY_BETWEEN_BATCHES = 2  # Segundos entre batches

def process_all_companies():
    """Procesa todas las empresas en mini batches"""
    offset = 0
    total_processed = 0
    total_enriched = 0
    total_contacts = 0
    start_time = time.time()
    batch_count = 0
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando procesamiento...")
    print(f"Procesando en batches de {BATCH_SIZE} empresas\n")
    
    while True:
        batch_count += 1
        print(f"Batch #{batch_count} - Offset: {offset}")
        
        try:
            # Hacer request con timeout corto
            response = requests.post(
                f"{API_URL}/enrich_mini_batch",
                headers={
                    "X-API-Key": API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "batch_size": BATCH_SIZE,
                    "start_offset": offset
                },
                timeout=120  # 2 minutos de timeout
            )
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                break
            
            data = response.json()
            
            if not data.get('success'):
                print(f"❌ Error: {data.get('error')}")
                break
            
            # Actualizar estadísticas
            results = data.get('results', {})
            batch_info = data.get('batch_info', {})
            
            companies_in_batch = results.get('companies_processed', 0)
            enriched_in_batch = results.get('companies_enriched', 0)
            contacts_in_batch = results.get('contacts_created', 0)
            
            total_processed += companies_in_batch
            total_enriched += enriched_in_batch
            total_contacts += contacts_in_batch
            
            # Mostrar progreso
            print(f"  ✓ Procesadas: {companies_in_batch} empresas")
            print(f"  ✓ Enriquecidas: {enriched_in_batch} empresas")
            print(f"  ✓ Contactos creados: {contacts_in_batch}")
            print(f"  ✓ Total acumulado: {total_processed} empresas\n")
            
            # Verificar si hay más empresas
            if not batch_info.get('has_more', False):
                print("✅ Procesamiento completado - No hay más empresas")
                break
            
            # Actualizar offset
            offset = batch_info.get('next_offset', offset + BATCH_SIZE)
            
            # Pausa entre batches
            print(f"⏳ Esperando {DELAY_BETWEEN_BATCHES} segundos antes del siguiente batch...\n")
            time.sleep(DELAY_BETWEEN_BATCHES)
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout en batch {batch_count} - Reintentando...")
            time.sleep(5)
            continue
            
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Error de conexión en batch {batch_count} - Reintentando en 10 segundos...")
            time.sleep(10)
            continue
            
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            break
    
    # Resumen final
    elapsed_time = time.time() - start_time
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"Tiempo total: {elapsed_time/60:.2f} minutos")
    print(f"Empresas procesadas: {total_processed}")
    print(f"Empresas enriquecidas: {total_enriched}")
    print(f"Contactos creados: {total_contacts}")
    print(f"Batches procesados: {batch_count}")
    print(f"Promedio por empresa: {elapsed_time/total_processed:.2f} segundos" if total_processed > 0 else "")
    print("="*60)

def estimate_time(total_companies):
    """Estima el tiempo necesario para procesar N empresas"""
    batches_needed = (total_companies + BATCH_SIZE - 1) // BATCH_SIZE
    # 10 segundos por batch (procesamiento + delay)
    estimated_seconds = batches_needed * 10
    return estimated_seconds / 60

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Uso: python3 process_without_timeout.py [--estimate N]")
            print("  --estimate N: Estima el tiempo para procesar N empresas")
            sys.exit(0)
        elif sys.argv[1] == "--estimate" and len(sys.argv) > 2:
            companies = int(sys.argv[2])
            minutes = estimate_time(companies)
            print(f"\nEstimación para {companies} empresas:")
            print(f"  - Batches necesarios: {(companies + BATCH_SIZE - 1) // BATCH_SIZE}")
            print(f"  - Tiempo estimado: {minutes:.1f} minutos")
            print(f"  - Sin riesgo de timeout (batches de {BATCH_SIZE} empresas)")
            sys.exit(0)
    
    # Ejecutar procesamiento
    try:
        process_all_companies()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        print("Puedes retomar desde el último offset procesado")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")