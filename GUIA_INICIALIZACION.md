# 🚀 Guía de Inicialización - Plataforma Belgrano Ahorro Tickets

## 📋 Resumen

Esta guía te explica todas las formas disponibles para inicializar la base de datos de la plataforma de tickets de Belgrano Ahorro.

## 🎯 Métodos de Inicialización

### 1. **Método Automático (Recomendado)**
La aplicación se inicializa automáticamente al ejecutarla por primera vez.

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Ejecutar la aplicación
python app.py
```

**Ventajas:**
- ✅ Automático
- ✅ Crea las tablas si no existen
- ✅ No requiere pasos adicionales

### 2. **Script de Inicialización Completa**
Script que verifica dependencias, crea la base de datos y valida todo el sistema.

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Ejecutar inicialización completa
python inicializar_plataforma.py
```

**Ventajas:**
- ✅ Verificación completa del sistema
- ✅ Crea usuarios predefinidos
- ✅ Muestra credenciales de acceso
- ✅ Valida que todo funcione correctamente

### 3. **Script de Creación Simple**
Script básico que solo crea la base de datos y usuarios.

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Crear base de datos
python crear_db_simple.py
```

**Ventajas:**
- ✅ Rápido y simple
- ✅ Solo crea la base de datos
- ✅ No requiere verificación

### 4. **Inicialización Manual con Flask**
Usar Flask-SQLAlchemy para crear las tablas manualmente.

```python
from app import app, db

with app.app_context():
    db.create_all()
    print("✅ Tablas creadas")
```

## 🔧 Requisitos Previos

### Dependencias Necesarias
```bash
pip install flask flask_sqlalchemy flask_login flask_socketio werkzeug
```

### Estructura de Archivos
```
belgrano_tickets/
├── app.py                 # Aplicación principal
├── models.py              # Modelos de base de datos
├── db_init.py             # Inicialización de SQLAlchemy
├── inicializar_plataforma.py  # Script completo
├── crear_db_simple.py     # Script simple
├── run.py                 # Script de ejecución
└── belgrano_tickets.db    # Base de datos SQLite
```

## 👥 Usuarios Creados Automáticamente

### 👑 Administrador
- **Email:** admin@belgranoahorro.com
- **Contraseña:** admin123
- **Rol:** admin
- **Funciones:** Gestión completa de tickets y usuarios

### 🚚 Cuentas de Flota
- **Repartidor 1:** repartidor1@belgranoahorro.com / repartidor123
- **Repartidor 2:** repartidor2@belgranoahorro.com / repartidor123
- **Repartidor 3:** repartidor3@belgranoahorro.com / repartidor123
- **Repartidor 4:** repartidor4@belgranoahorro.com / repartidor123
- **Repartidor 5:** repartidor5@belgranoahorro.com / repartidor123

## 🗄️ Estructura de la Base de Datos

### Tabla `user`
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    role VARCHAR(20) NOT NULL,
    nombre VARCHAR(50)
);
```

### Tabla `ticket`
```sql
CREATE TABLE ticket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero VARCHAR(50) UNIQUE NOT NULL,
    cliente_nombre VARCHAR(120),
    cliente_direccion VARCHAR(200),
    cliente_telefono VARCHAR(50),
    cliente_email VARCHAR(120),
    productos TEXT,
    estado VARCHAR(20) DEFAULT 'pendiente',
    prioridad VARCHAR(20) DEFAULT 'normal',
    indicaciones TEXT,
    asignado_a INTEGER,
    repartidor VARCHAR(50),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asignado_a) REFERENCES user (id)
);
```

## 🌐 Acceso a la Aplicación

### URL de Acceso
- **Local:** http://localhost:5001
- **Puerto:** 5001

### Endpoints Principales
- **Login:** http://localhost:5001/login
- **Panel Admin:** http://localhost:5001/panel
- **API Tickets:** http://localhost:5001/api/tickets/recibir

## 🔗 Integración con Belgrano Ahorro

### Endpoint para Recibir Tickets
```
POST http://localhost:5001/api/tickets/recibir
Content-Type: application/json
```

### Formato JSON Esperado
```json
{
    "numero": "TICKET-001",
    "cliente_nombre": "Juan Pérez",
    "cliente_direccion": "Av. Belgrano 123",
    "cliente_telefono": "123456789",
    "cliente_email": "juan@email.com",
    "productos": [
        {
            "nombre": "Producto 1",
            "cantidad": 2,
            "precio": 100.00
        }
    ],
    "estado": "pendiente",
    "prioridad": "normal",
    "indicaciones": "Entregar antes de las 18:00"
}
```

## 🚀 Comandos Útiles

### Iniciar la Aplicación
```bash
# Método 1: Script de ejecución
python run.py

# Método 2: Directo
python app.py
```

### Verificar Base de Datos
```bash
# Verificar tablas
python verificar_tablas.py

# Verificar usuarios
python verificar_usuarios.py
```

### Recrear Base de Datos
```bash
# Recrear desde cero
python recreate_db.py
```

## 🔍 Solución de Problemas

### Error: "No module named 'werkzeug'"
```bash
# Activar entorno virtual
.venv\Scripts\activate

# Instalar dependencias
pip install werkzeug flask flask_sqlalchemy flask_login flask_socketio
```

### Error: "Base de datos no encontrada"
```bash
# Ejecutar inicialización
python inicializar_plataforma.py
```

### Error: "Puerto 5001 en uso"
```bash
# Cambiar puerto en app.py
socketio.run(app, debug=True, host='0.0.0.0', port=5002)
```

## 📊 Funcionalidades Disponibles

### Para Administradores
- ✅ Gestión completa de tickets
- ✅ Asignación de repartidores
- ✅ Gestión de usuarios
- ✅ Reportes y estadísticas
- ✅ Panel de control

### Para Flota
- ✅ Ver tickets asignados
- ✅ Actualizar estado de tickets
- ✅ Ver detalles de clientes
- ✅ Panel simplificado

### Integración en Tiempo Real
- ✅ WebSocket para actualizaciones
- ✅ Notificaciones automáticas
- ✅ Sincronización instantánea

## 🎉 ¡Listo para Usar!

Una vez completada la inicialización, tu plataforma de tickets estará lista para:

1. **Recibir tickets** desde la aplicación principal de Belgrano Ahorro
2. **Gestionar entregas** con el equipo de flota
3. **Monitorear** el estado de todos los pedidos
4. **Generar reportes** de rendimiento

¡La integración con Belgrano Ahorro está completa y funcionando!
