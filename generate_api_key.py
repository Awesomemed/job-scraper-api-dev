#!/usr/bin/env python3
"""
Script para generar API keys seguros
"""

import secrets
import string
import hashlib
import uuid
import base64

def generate_simple_key(length=32):
    """Genera una API key simple con caracteres alfanuméricos"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_uuid_key():
    """Genera una API key basada en UUID"""
    return str(uuid.uuid4())

def generate_hex_key(length=32):
    """Genera una API key en formato hexadecimal"""
    return secrets.token_hex(length)

def generate_urlsafe_key(length=32):
    """Genera una API key segura para URLs"""
    return secrets.token_urlsafe(length)

def generate_prefixed_key(prefix="sk"):
    """Genera una API key con prefijo (como las de Stripe)"""
    key = secrets.token_urlsafe(32)
    return f"{prefix}_{key}"

def generate_hash_based_key(seed=None):
    """Genera una API key basada en hash SHA256"""
    if seed is None:
        seed = secrets.token_bytes(32)
    else:
        seed = seed.encode('utf-8')
    
    hash_object = hashlib.sha256(seed)
    return hash_object.hexdigest()

def generate_base64_key():
    """Genera una API key en formato base64"""
    random_bytes = secrets.token_bytes(32)
    return base64.b64encode(random_bytes).decode('utf-8')

if __name__ == "__main__":
    print("=== Generador de API Keys ===\n")
    
    print("1. API Key Simple (32 caracteres):")
    print(f"   {generate_simple_key()}\n")
    
    print("2. API Key basada en UUID:")
    print(f"   {generate_uuid_key()}\n")
    
    print("3. API Key Hexadecimal:")
    print(f"   {generate_hex_key()}\n")
    
    print("4. API Key URL-Safe (recomendada):")
    key = generate_urlsafe_key()
    print(f"   {key}\n")
    
    print("5. API Key con Prefijo:")
    print(f"   {generate_prefixed_key('api')}\n")
    
    print("6. API Key basada en Hash:")
    print(f"   {generate_hash_based_key()}\n")
    
    print("7. API Key Base64:")
    print(f"   {generate_base64_key()}\n")
    
    print("\n💡 Recomendación: Usa la opción 4 (URL-Safe) para tu API")
    print(f"\n✅ Tu API Key recomendada es:\n   {generate_urlsafe_key(48)}")
    
    print("\n📝 Instrucciones:")
    print("1. Copia la API key generada")
    print("2. Guárdala en tu archivo .env como: API_KEY=tu-key-aqui")
    print("3. Nunca compartas esta key públicamente")
    print("4. Úsala en n8n en el header: X-API-Key: tu-key-aqui")