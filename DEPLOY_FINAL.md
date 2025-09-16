# 🚀 DEPLOY FINAL - BELGRANO TICKETS

## ✅ Estado Actual
- **Usuarios creados:** ✅ 8 usuarios (1 admin + 7 flota)
- **Base de datos:** ✅ Inicializada
- **Dockerfile:** ✅ Optimizado para Render
- **Scripts:** ✅ Configurados para crear usuarios automáticamente
- **Verificación:** ✅ 7/7 verificaciones exitosas

## 📋 Credenciales de Acceso

En producción no se deben publicar credenciales. Para desarrollo local, el sistema puede inicializar usuarios demo (admin y flota). En producción, crea usuarios reales en la base de datos y deshabilita cualquier endpoint de debug.

## 🐳 Opciones de Deploy

### **Opción 1: Deploy con Docker (Recomendado)**
```bash
# Usar el archivo render_docker.yaml
# Render automáticamente:
# - Detecta el Dockerfile
# - Construye la imagen Docker
# - Crea usuarios automáticamente
# - Inicia con gunicorn
```

### **Opción 2: Deploy Nativo Python**
```bash
# Usar el archivo render_independiente.yaml
# Render ejecuta:
# - pip install -r requirements_ticketera.txt
# - python app.py
```

## ⚙️ Variables de Entorno Requeridas

```yaml
# En render_docker.yaml
envVars:
  - key: FLASK_ENV
    value: production
  - key: PORT
    value: 5000
  - key: SECRET_KEY
    value: ${GENERAR_UNA_SECRETA_UNICA}
  - key: DATABASE_URL
    value: ${URL_DE_BASE_DE_DATOS_NO_SQLITE_EN_PROD}
  - key: BELGRANO_AHORRO_URL
    value: https://belgrano-ahorro.onrender.com
  - key: BELGRANO_AHORRO_API_KEY
    value: ${API_KEY}
  - key: TICKETS_API_URL
    value: https://tu-ticketera/api/tickets
  - key: TICKETS_API_KEY
    value: ${API_KEY_OPCIONAL}
  - key: TICKETS_API_USERNAME
    value: ${USUARIO_OPCIONAL}
  - key: TICKETS_API_PASSWORD
    value: ${PASSWORD_OPCIONAL}
  - key: BELGRANO_AHORRO_TIMEOUT
    value: 30
```

## 🔧 Scripts de Inicio

### **Procfile (Render/Heroku)**
Usamos gunicorn apuntando a `app_unificado:app`:

```bash
web: gunicorn app_unificado:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100
```

### **Verificación Local**
```bash
python verificar_deploy.py
# Resultado esperado: 7/7 verificaciones exitosas
```

## 📁 Estructura de Archivos

```
belgrano_tickets/
├── app_unificado.py                # Aplicación principal (Ahorro + Ticketera)
├── models.py                       # Modelos de base de datos
├── belgrano_tickets/config.py      # Configuración centralizada
├── requirements_ticketera.txt      # Dependencias Python
├── Dockerfile                      # Configuración Docker
├── start_ticketera.sh              # Script de inicio
├── belgrano_client.py              # Cliente API
├── templates/                      # Plantillas HTML
├── static/                         # Archivos estáticos
├── belgrano_tickets.db             # Base de datos SQLite
├── render_docker.yaml              # Config Render Docker
├── render_independiente.yaml       # Config Render Python
├── verificar_deploy.py             # Script de verificación
├── mostrar_credenciales.py         # Mostrar credenciales
└── .dockerignore                   # Excluir archivos Docker
```

## 🚀 Pasos para Deploy

### **1. Preparación**
```bash
# Verificar configuración
python verificar_deploy.py

# Ver credenciales
python mostrar_credenciales.py
```

### **2. Deploy en Render**
1. Ir a [Render.com](https://render.com)
2. Crear nuevo Web Service
3. Conectar repositorio GitHub
4. Usar archivo `render_docker.yaml` o `render_independiente.yaml`
5. Configurar variables de entorno
6. Deploy

### **3. Verificación Post-Deploy**
1. Acceder a la URL del servicio
2. Login con credenciales:
   - Admin: `admin@belgrano.com` / `admin123`
   - Flota: `flota1@belgrano.com` / `flota123`
3. Verificar funcionalidades

## 🔗 URLs Importantes

- **Aplicación:** `https://[nombre-servicio].onrender.com`
- **Health Check:** `https://[nombre-servicio].onrender.com/health`
- **API Tickets:** `https://[nombre-servicio].onrender.com/api/tickets`

## 📊 Monitoreo

### **Logs de Render**
- Verificar logs durante el deploy
- Buscar mensajes de inicialización de usuarios
- Confirmar conexión con Belgrano Ahorro

### **Health Check**
- Endpoint: `/health`
- Verifica que la aplicación esté funcionando
- Render lo usa para monitoreo automático

## ✅ Checklist Final

- [x] Usuarios admin y flota creados
- [x] Base de datos inicializada
- [x] Dockerfile optimizado
- [x] Scripts de inicio configurados
- [x] Variables de entorno definidas
- [x] Verificación local exitosa
- [x] Archivos de configuración Render listos
- [x] Documentación completa

## 🎉 ¡Listo para Deploy!

**El sistema está completamente configurado y listo para deploy en Render.com con usuarios admin y flota automáticamente creados.**
