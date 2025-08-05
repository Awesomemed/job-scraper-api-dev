#!/bin/bash

# Métodos rápidos para generar API keys

echo "=== Métodos rápidos para generar API Keys ==="
echo ""

# Método 1: OpenSSL
echo "1. Con OpenSSL (32 bytes):"
openssl rand -base64 32 2>/dev/null || echo "   OpenSSL no disponible"
echo ""

# Método 2: /dev/urandom
echo "2. Con /dev/urandom:"
cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1
echo ""

# Método 3: UUID
echo "3. Con UUID:"
uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "   UUID no disponible"
echo ""

# Método 4: Date + Random
echo "4. Con fecha y random:"
echo "api_$(date +%s)_$(head -c 16 /dev/urandom | base64 | tr -d '=' | tr '+/' '-_')"
echo ""

# Método 5: Python one-liner
echo "5. Con Python one-liner:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "   Python no disponible"
echo ""