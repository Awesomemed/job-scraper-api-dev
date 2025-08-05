#!/usr/bin/env python3
"""
Script para generar SECRET_KEY para Flask
"""

import secrets
import os
import base64
import hashlib
from datetime import datetime

def generate_flask_secret_key():
    """Genera una SECRET_KEY segura para Flask (método recomendado)"""
    return secrets.token_hex(32)

def generate_complex_secret_key():
    """Genera una SECRET_KEY más compleja"""
    # Combina múltiples fuentes de entropía
    timestamp = str(datetime.now().timestamp()).encode()
    random_bytes = os.urandom(32)
    
    # Crear un hash combinado
    combined = timestamp + random_bytes
    return hashlib.sha256(combined).hexdigest()

def generate_urlsafe_secret_key():
    """Genera una SECRET_KEY URL-safe"""
    return secrets.token_urlsafe(32)

def generate_base64_secret_key():
    """Genera una SECRET_KEY en base64"""
    return base64.b64encode(os.urandom(32)).decode('utf-8')

def generate_strong_secret_key():
    """Genera una SECRET_KEY extra fuerte"""
    # 64 bytes de entropía
    return secrets.token_hex(64)

print("=== Generador de SECRET_KEY para Flask ===\n")

print("SECRET_KEY es usada por Flask para:")
print("- Firmar cookies de sesión")
print("- Proteger contra CSRF")
print("- Generar tokens seguros")
print("- Encriptar datos sensibles\n")

print("1. SECRET_KEY Estándar (Recomendada):")
key1 = generate_flask_secret_key()
print(f"   {key1}")
print(f"   Longitud: {len(key1)} caracteres\n")

print("2. SECRET_KEY Compleja:")
key2 = generate_complex_secret_key()
print(f"   {key2}\n")

print("3. SECRET_KEY URL-Safe:")
key3 = generate_urlsafe_secret_key()
print(f"   {key3}\n")

print("4. SECRET_KEY Base64:")
key4 = generate_base64_secret_key()
print(f"   {key4}\n")

print("5. SECRET_KEY Extra Fuerte (128 caracteres):")
key5 = generate_strong_secret_key()
print(f"   {key5}\n")

print("\n✅ SECRET_KEY recomendada para tu aplicación:")
recommended_key = secrets.token_hex(32)
print(f"   {recommended_key}\n")

print("📝 Instrucciones de uso:")
print("1. Copia la SECRET_KEY generada")
print("2. Agrégala a tu archivo .env:")
print(f"   SECRET_KEY={recommended_key}")
print("3. NUNCA commits el archivo .env a git")
print("4. Usa una SECRET_KEY diferente en producción")
print("5. NO cambies la SECRET_KEY una vez en producción (invalidará todas las sesiones)")

print("\n⚠️  IMPORTANTE:")
print("- La SECRET_KEY debe ser ÚNICA para cada aplicación")
print("- Debe mantenerse PRIVADA y SEGURA")
print("- Si se compromete, todas las sesiones deben ser invalidadas")
print("- Usa al menos 32 bytes de entropía (64 caracteres hex)")

# Guardar ejemplo en archivo
print("\n💾 ¿Deseas guardar un archivo .env de ejemplo? (s/n): ", end="")
try:
    respuesta = input().strip().lower()
    if respuesta == 's':
        env_content = f"""# Flask Configuration
SECRET_KEY={recommended_key}
FLASK_ENV=production

# API Authentication
API_KEY={secrets.token_urlsafe(32)}

# Apollo.io Configuration
APOLLO_API_KEY=your-apollo-api-key

# Zoho CRM Configuration
ZOHO_CLIENT_ID=your-zoho-client-id
ZOHO_CLIENT_SECRET=your-zoho-client-secret
ZOHO_REFRESH_TOKEN=your-zoho-refresh-token
ZOHO_DOMAIN=https://www.zohoapis.com
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("\n✅ Archivo .env creado con SECRET_KEY y API_KEY generadas!")
        print("   Recuerda actualizar las credenciales de Apollo y Zoho.")
except:
    pass