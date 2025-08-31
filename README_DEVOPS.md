# Panel de DevOps - Belgrano Tickets

## Descripción

El Panel de DevOps es un sistema de gestión exclusivo para administradores que permite modificar automáticamente todos los elementos de Belgrano Ahorro desde la ticketera. Este panel proporciona acceso completo a la gestión de productos, sucursales, negocios, ofertas y precios.

## Características Principales

### 🔐 Autenticación Segura
- Login independiente con credenciales específicas de DevOps
- Sesiones separadas del sistema principal
- Acceso restringido solo a personal autorizado

### 📊 Dashboard Centralizado
- Estadísticas en tiempo real de Belgrano Ahorro
- Vista general de productos, sucursales, negocios y ofertas
- Estado del sistema y conectividad API
- Actividad reciente de modificaciones

### 🛠️ Gestión Completa de Contenido

#### Productos
- ✅ Agregar nuevos productos
- ✅ Editar productos existentes
- ✅ Eliminar productos
- ✅ Gestionar categorías, precios y stock
- ✅ Activar/desactivar productos

#### Sucursales
- ✅ Agregar nuevas sucursales
- ✅ Editar información de sucursales
- ✅ Eliminar sucursales
- ✅ Gestionar direcciones, teléfonos y emails
- ✅ Activar/desactivar sucursales

#### Negocios
- ✅ Agregar nuevos negocios
- ✅ Editar información de negocios
- ✅ Eliminar negocios
- ✅ Gestionar categorías y contactos
- ✅ Activar/desactivar negocios

#### Ofertas
- ✅ Crear nuevas ofertas
- ✅ Editar ofertas existentes
- ✅ Eliminar ofertas
- ✅ Gestionar descuentos y fechas
- ✅ Vincular ofertas a productos específicos

#### Precios
- ✅ Actualización masiva de precios
- ✅ Aumentar/reducir precios por porcentaje
- ✅ Establecer precios fijos
- ✅ Filtrado por categorías
- ✅ Vista previa de cambios antes de aplicar

## Acceso al Panel

### URL de Acceso
```
http://localhost:5000/devops/login
```

### Credenciales por Defecto
- **Usuario:** `devops`
- **Contraseña:** `devops2025`

### Configuración de Variables de Entorno
```bash
# Credenciales DevOps
DEVOPS_USERNAME=devops
DEVOPS_PASSWORD=devops2025

# Configuración API Belgrano Ahorro
BELGRANO_AHORRO_URL=http://localhost:5000
BELGRANO_AHORRO_API_KEY=belgrano_ahorro_api_key_2025
```

## Estructura de Archivos

```
belgrano_tickets/
├── devops_routes.py              # Rutas y lógica del panel DevOps
├── templates/devops/
│   ├── login.html               # Página de login DevOps
│   ├── dashboard.html           # Dashboard principal
│   ├── productos.html           # Gestión de productos
│   ├── sucursales.html          # Gestión de sucursales
│   ├── negocios.html            # Gestión de negocios
│   ├── ofertas.html             # Gestión de ofertas
│   └── precios.html             # Gestión de precios
└── README_DEVOPS.md             # Esta documentación
```

## Funcionalidades Detalladas

### 1. Gestión de Productos

#### Agregar Producto
1. Navegar a `/devops/productos`
2. Hacer clic en "Agregar Producto"
3. Completar formulario:
   - Nombre del producto
   - Descripción
   - Precio
   - Categoría
   - Stock inicial
4. Guardar producto

#### Editar Producto
1. En la lista de productos, hacer clic en el botón de editar
2. Modificar los campos necesarios
3. Marcar/desmarcar "Producto Activo" según corresponda
4. Guardar cambios

#### Eliminar Producto
1. En la lista de productos, hacer clic en el botón de eliminar
2. Confirmar la eliminación
3. El producto se elimina permanentemente

### 2. Gestión de Sucursales

#### Agregar Sucursal
1. Navegar a `/devops/sucursales`
2. Hacer clic en "Agregar Sucursal"
3. Completar formulario:
   - Nombre de la sucursal
   - Dirección completa
   - Teléfono
   - Email
   - Ciudad
4. Guardar sucursal

#### Editar Sucursal
1. En la lista de sucursales, hacer clic en el botón de editar
2. Modificar la información necesaria
3. Marcar/desmarcar "Sucursal Activa" según corresponda
4. Guardar cambios

### 3. Gestión de Negocios

#### Agregar Negocio
1. Navegar a `/devops/negocios`
2. Hacer clic en "Agregar Negocio"
3. Completar formulario:
   - Nombre del negocio
   - Descripción
   - Categoría
   - Dirección
   - Teléfono
   - Email
4. Guardar negocio

### 4. Gestión de Ofertas

#### Crear Oferta
1. Navegar a `/devops/ofertas`
2. Hacer clic en "Crear Oferta"
3. Completar formulario:
   - Título de la oferta
   - Descripción
   - Producto asociado
   - Porcentaje de descuento
   - Fecha de inicio
   - Fecha de fin
4. Guardar oferta

### 5. Gestión de Precios

#### Actualización Masiva
1. Navegar a `/devops/precios`
2. Usar las herramientas de acciones masivas:
   - **Aumentar/Reducir (%):** Ingresar porcentaje
   - **Categoría:** Seleccionar categoría específica (opcional)
   - **Acción:** Elegir entre aumentar, reducir o establecer precio fijo
3. Hacer clic en "Aplicar" para ver los cambios
4. Revisar los cambios en la tabla
5. Hacer clic en "Aplicar Cambios" para confirmar

#### Edición Individual
1. En la tabla de precios, modificar directamente los valores
2. Los cambios se muestran en tiempo real con indicadores de porcentaje
3. Usar "Revertir" para cancelar cambios no guardados
4. Hacer clic en "Aplicar Cambios" para guardar

## API Endpoints Utilizados

El panel DevOps se comunica con Belgrano Ahorro a través de los siguientes endpoints:

### Productos
- `GET /api/productos` - Obtener lista de productos
- `POST /api/productos` - Crear nuevo producto
- `PUT /api/productos/{id}` - Actualizar producto
- `DELETE /api/productos/{id}` - Eliminar producto

### Sucursales
- `GET /api/sucursales` - Obtener lista de sucursales
- `POST /api/sucursales` - Crear nueva sucursal
- `PUT /api/sucursales/{id}` - Actualizar sucursal
- `DELETE /api/sucursales/{id}` - Eliminar sucursal

### Negocios
- `GET /api/negocios` - Obtener lista de negocios
- `POST /api/negocios` - Crear nuevo negocio
- `PUT /api/negocios/{id}` - Actualizar negocio
- `DELETE /api/negocios/{id}` - Eliminar negocio

### Ofertas
- `GET /api/ofertas` - Obtener lista de ofertas
- `POST /api/ofertas` - Crear nueva oferta
- `PUT /api/ofertas/{id}` - Actualizar oferta
- `DELETE /api/ofertas/{id}` - Eliminar oferta

### Precios
- `GET /api/precios` - Obtener lista de precios
- `POST /api/precios/actualizar-masivo` - Actualizar precios masivamente

### Estadísticas
- `GET /api/stats` - Obtener estadísticas del sistema

## Seguridad

### Autenticación
- Credenciales independientes del sistema principal
- Sesiones separadas con timeout automático
- Logout automático al cerrar navegador

### Autorización
- Acceso restringido solo a usuarios DevOps
- Decorador `@devops_required` en todas las rutas
- Verificación de sesión en cada request

### Logging
- Registro de todas las operaciones realizadas
- Logs de errores y excepciones
- Auditoría de cambios realizados

## Configuración de Producción

### Variables de Entorno Recomendadas
```bash
# Credenciales DevOps (CAMBIAR EN PRODUCCIÓN)
DEVOPS_USERNAME=admin_devops
DEVOPS_PASSWORD=password_seguro_complejo_2025

# Configuración API
BELGRANO_AHORRO_URL=https://belgranoahorro-hp30.onrender.com
BELGRANO_AHORRO_API_KEY=api_key_segura_produccion

# Configuración de seguridad
FLASK_SECRET_KEY=clave_secreta_muy_segura_produccion
```

### Consideraciones de Seguridad
1. **Cambiar credenciales por defecto** inmediatamente en producción
2. **Usar HTTPS** para todas las comunicaciones
3. **Implementar rate limiting** para prevenir ataques de fuerza bruta
4. **Configurar logs de auditoría** para rastrear todas las modificaciones
5. **Backup automático** antes de operaciones masivas
6. **Notificaciones** para cambios críticos

## Mantenimiento

### Verificación de Conectividad
El panel verifica automáticamente la conectividad con Belgrano Ahorro y muestra el estado en el dashboard.

### Logs de Error
Los errores se registran en el log del sistema y se muestran al usuario con mensajes descriptivos.

### Backup y Restauración
Se recomienda realizar backups regulares de la base de datos antes de operaciones masivas.

## Soporte

Para reportar problemas o solicitar nuevas funcionalidades:

1. Revisar los logs del sistema
2. Verificar la conectividad con Belgrano Ahorro
3. Comprobar las credenciales de acceso
4. Contactar al equipo de desarrollo

## Changelog

### v1.0.0 (2025-01-27)
- ✅ Panel de DevOps completo
- ✅ Gestión de productos, sucursales, negocios, ofertas y precios
- ✅ Autenticación segura
- ✅ Dashboard con estadísticas
- ✅ Actualización masiva de precios
- ✅ Interfaz moderna y responsive
