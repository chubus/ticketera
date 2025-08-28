#!/bin/bash
# -*- coding: utf-8 -*-
"""
Script de inicio para la Ticketera
Inicializa la base de datos de forma segura y arranca el servidor Gunicorn
"""

set -e  # Salir si cualquier comando falla

echo "🚀 Iniciando Ticketera..."
echo "================================"

# Función para manejar errores
handle_error() {
    echo "❌ Error en el script: $1"
    exit 1
}

# Función para verificar dependencias
check_dependencies() {
    echo "🔍 Verificando dependencias..."
    
    if ! command -v python3 &> /dev/null; then
        handle_error "Python3 no está instalado"
    fi
    
    if ! command -v gunicorn &> /dev/null; then
        handle_error "Gunicorn no está instalado"
    fi
    
    echo "✅ Dependencias verificadas"
}

# Función para inicializar la base de datos
init_database() {
    echo "🗄️ Inicializando base de datos..."
    
    # Verificar que el script de inicialización existe
    if [ ! -f "scripts/init_users_flota.py" ]; then
        handle_error "Script de inicialización no encontrado: scripts/init_users_flota.py"
    fi
    
    # Actualizar esquema de base de datos primero
    echo "🔧 Actualizando esquema de base de datos..."
    if python3 actualizar_db.py; then
        echo "✅ Esquema de base de datos actualizado"
    else
        echo "⚠️ Error actualizando esquema, continuando..."
    fi
    
    # Ejecutar script de inicialización
    if python3 scripts/init_users_flota.py; then
        echo "✅ Base de datos inicializada correctamente"
    else
        handle_error "Error inicializando la base de datos"
    fi
}

# Función para verificar variables de entorno
check_environment() {
    echo "🔧 Verificando variables de entorno..."
    
    # Variables requeridas
    required_vars=("BELGRANO_AHORRO_URL" "BELGRANO_AHORRO_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "⚠️ Variable de entorno $var no está definida"
        else
            echo "✅ $var está configurada"
        fi
    done
    
    # Puerto por defecto
    export PORT=${PORT:-10000}
    echo "✅ Puerto configurado: $PORT"
}

# Función para arrancar el servidor
start_server() {
    echo "🌐 Arrancando servidor Gunicorn..."
    echo "   Puerto: $PORT"
    echo "   Worker class: gevent"
    echo "   Bind: 0.0.0.0:$PORT"
    echo "================================"
    
    # Comando Gunicorn con gevent para Socket.IO
    exec gunicorn \
        --worker-class gevent \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        wsgi:app
}

# Función principal
main() {
    echo "🎯 Ticketera - Script de Inicio"
    echo "================================"
    
    # Cambiar al directorio del script si es necesario
    cd "$(dirname "$0")"
    
    # Verificar dependencias
    check_dependencies
    
    # Verificar variables de entorno
    check_environment
    
    # Inicializar base de datos
    init_database
    
    # Arrancar servidor
    start_server
}

# Ejecutar función principal
main "$@"
