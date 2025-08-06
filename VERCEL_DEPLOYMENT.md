# Vercel Deployment Guide

## Configuración de Variables de Entorno

Para desplegar esta API en Vercel, necesitas configurar las siguientes variables de entorno en el dashboard de Vercel:

### Variables Requeridas

1. **API_KEY** - Tu clave de API para autenticación
2. **APOLLO_API_KEY** - Clave de API de Apollo.io
3. **ZOHO_CLIENT_ID** - ID de cliente OAuth de Zoho
4. **ZOHO_CLIENT_SECRET** - Secreto de cliente OAuth de Zoho
5. **ZOHO_REFRESH_TOKEN** - Token de actualización OAuth de Zoho

### Pasos para Configurar en Vercel

1. Ve a tu proyecto en [Vercel Dashboard](https://vercel.com/dashboard)
2. Haz clic en "Settings" → "Environment Variables"
3. Agrega cada variable de entorno:
   - Name: El nombre de la variable (ej: `API_KEY`)
   - Value: El valor correspondiente
   - Environment: Selecciona "Production", "Preview", y "Development"
4. Haz clic en "Save" para cada variable

### Estructura del Proyecto para Vercel

```
job-scraper-api-dev/
├── api/
│   └── index.py          # Función serverless principal
├── requirements.txt      # Dependencias de Python
├── vercel.json          # Configuración de Vercel
└── .env.example         # Ejemplo de variables de entorno
```

### Configuración de vercel.json

El archivo `vercel.json` está configurado para:
- Usar Python como runtime
- Establecer un timeout máximo de 60 segundos
- Redirigir todas las rutas a la función `/api`

### Endpoints Disponibles

Una vez desplegado, tu API estará disponible en:
- `https://tu-proyecto.vercel.app/` - Información de la API
- `https://tu-proyecto.vercel.app/health` - Health check
- `https://tu-proyecto.vercel.app/scrape` - Scraping de trabajos
- `https://tu-proyecto.vercel.app/enrich_contacts` - Enriquecimiento de contactos
- Y todos los demás endpoints documentados en la raíz de la API

### Consideraciones Importantes

1. **Timeouts**: Vercel tiene un límite de timeout de 60 segundos para funciones serverless en el plan gratuito
2. **Límites de Memoria**: Las funciones tienen un límite de 1024 MB de RAM
3. **Logs**: Puedes ver los logs en el dashboard de Vercel bajo "Functions" → "Logs"

### Verificar el Despliegue

Después del despliegue, verifica que tu API funcione correctamente:

```bash
# Health check (sin autenticación)
curl https://tu-proyecto.vercel.app/health

# Test de autenticación
curl -H "X-API-Key: tu-api-key" https://tu-proyecto.vercel.app/test-auth
```

### Solución de Problemas

1. **Error 500**: Revisa los logs en Vercel para ver el error específico
2. **Timeout errors**: Usa los endpoints de procesamiento por lotes (`/enrich_mini_batch`)
3. **Variables de entorno no encontradas**: Asegúrate de que todas estén configuradas en Vercel

### Notas sobre Rendimiento

Para operaciones largas, considera usar:
- `/enrich_mini_batch` - Procesa solo 5 empresas a la vez
- `/enrich_companies_chunked` - Procesamiento por bloques con paginación

Estos endpoints están optimizados para funcionar dentro de los límites de tiempo de Vercel.