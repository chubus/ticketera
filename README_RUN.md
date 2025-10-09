# 🚀 Script de Inicio - Ticketera

## 📋 Descripción

El script `run.sh` es el punto de entrada principal para la Ticketera. Se encarga de:

1. **Inicializar la base de datos** de forma segura
2. **Crear usuarios** sin duplicados
3. **Arrancar el servidor** Gunicorn con Socket.IO

## 🛠️ Archivos Creados

### **`run.sh`** - Script principal
- ✅ Verifica dependencias (Python3, Gunicorn)
- ✅ Verifica variables de entorno
- ✅ Inicializa base de datos
- ✅ Arranca servidor Gunicorn con gevent

### **`scripts/init_users_flota.py`** - Inicialización de usuarios
- ✅ Crea base de datos si no existe
- ✅ Verifica usuarios existentes
- ✅ Crea usuarios sin duplicados
- ✅ Manejo de errores robusto

### **`wsgi.py`** - Punto de entrada WSGI
- ✅ Configurado para Gunicorn
- ✅ Soporte para Socket.IO
- ✅ Configuración de producción

## 🔧 Configuración

### **Variables de Entorno Requeridas**
```bash
BELGRANO_AHORRO_URL=https://belgranoahorro.onrender.com
BELGRANO_AHORRO_API_KEY=belgrano_ahorro_api_key_2025
PORT=10000  # Opcional, por defecto 10000
```

### **Dependencias**
```bash
# Instaladas automáticamente via requirements_ticketera.txt
Flask==3.1.1
Flask-SocketIO==5.3.6
gunicorn
gevent==23.9.1
eventlet==0.35.2
```

## 🚀 Uso

### **Ejecución Local**
```bash
cd belgrano_tickets
./run.sh
```

### **Ejecución en Docker**
```bash
# El Dockerfile ya está configurado para usar run.sh
docker build -t ticketera .
docker run -p 10000:10000 ticketera
```

### **Ejecución en Render**
- ✅ El Dockerfile usa `CMD ["./run.sh"]`
- ✅ Variables de entorno configuradas automáticamente
- ✅ Puerto dinámico via variable `$PORT`

## 📊 Usuarios Creados

### **Administrador**
- **Email**: admin@belgranoahorro.com
- **Password**: admin123
- **Rol**: admin

### **Flota (5 usuarios)**
- **Email**: repartidor1@belgranoahorro.com
- **Password**: flota123
- **Rol**: flota

*Repetido para repartidor2 hasta repartidor5*

## 🔍 Verificación

### **Health Check**
```bash
curl http://localhost:10000/healthz
# Debe devolver: "ok"
```

### **Logs Esperados**
```
🚀 Iniciando Ticketera...
🔍 Verificando dependencias...
✅ Dependencias verificadas
🔧 Verificando variables de entorno...
✅ BELGRANO_AHORRO_URL está configurada
✅ BELGRANO_AHORRO_API_KEY está configurada
🗄️ Inicializando base de datos...
✅ Base de datos inicializada correctamente
🌐 Arrancando servidor Gunicorn...
```

## 🛡️ Características de Seguridad

### **Inicialización Segura**
- ✅ Verifica usuarios existentes antes de crear
- ✅ No duplica usuarios
- ✅ Rollback en caso de error
- ✅ Logs detallados

### **Manejo de Errores**
- ✅ Script sale si cualquier comando falla (`set -e`)
- ✅ Verificación de dependencias
- ✅ Verificación de archivos requeridos
- ✅ Manejo de errores de base de datos

### **Configuración Robusta**
- ✅ Worker class gevent para Socket.IO
- ✅ Timeout configurado (120s)
- ✅ Keep-alive configurado (5s)
- ✅ Logs de acceso y error

## 🧪 Testing

### **Script de Prueba**
```bash
./test_run.sh
```

### **Verificaciones**
- ✅ Archivos requeridos existen
- ✅ Dependencias instaladas
- ✅ Configuración correcta

## 📝 Notas Importantes

1. **Puerto**: El script usa la variable `$PORT` o 10000 por defecto
2. **Base de datos**: Se crea automáticamente si no existe
3. **Usuarios**: Solo se crean si no existen
4. **Socket.IO**: Configurado con gevent para mejor rendimiento
5. **Logs**: Se muestran en stdout/stderr para Docker

---

**Estado**: ✅ **LISTO PARA PRODUCCIÓN**
