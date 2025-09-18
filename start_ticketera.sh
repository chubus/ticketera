#!/bin/bash

# Script de inicio para Belgrano Tickets en produccion
# Este script inicializa la base de datos, crea usuarios y ejecuta la aplicacion

set -e  # Salir si hay algun error

echo "Iniciando Belgrano Tickets..."
echo "Inicializando base de datos y usuarios..."

# Cambiar al directorio de la aplicacion
cd /app

# Verificar que el archivo app.py existe
if [ ! -f "app.py" ]; then
    echo "Error: app.py no encontrado en /app/"
    exit 1
fi

# Inicializar la base de datos y crear usuarios
echo "Inicializando base de datos y usuarios..."
python recrear_credenciales.py

# Verificar conexion con Belgrano Ahorro
echo "Verificando conexion con Belgrano Ahorro..."
echo "   URL: $BELGRANO_AHORRO_URL"

# Verificar variables de entorno
echo "Configuracion:"
echo "   Puerto: $PORT"
echo "   Entorno: $FLASK_ENV"
echo "   App: $FLASK_APP"

# Mostrar credenciales de acceso
echo "Credenciales de acceso disponibles:"
echo "   Admin: admin@belgranoahorro.com / admin123"
echo "   Flota: repartidor1@belgranoahorro.com / flota123 (y otros 6 usuarios flota)"

# Iniciar la aplicacion
echo "Iniciando aplicacion en puerto $PORT..."
echo "La ticketera estara disponible en http://localhost:$PORT"

# Ejecutar la aplicacion con gunicorn para produccion
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
