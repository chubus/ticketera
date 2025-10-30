#!/bin/sh
set -e

echo "🚀 Iniciando Ticketera..."

export FLASK_ENV=${FLASK_ENV:-production}
export PORT=${PORT:-5001}

# Verificar variables críticas en producción
if [ "$FLASK_ENV" = "production" ]; then
  if [ -z "$BELGRANO_AHORRO_URL" ] || [ -z "$BELGRANO_AHORRO_API_KEY" ]; then
    echo "❌ Variables BELGRANO_AHORRO_URL y/o BELGRANO_AHORRO_API_KEY faltan"
    exit 1
  fi
  if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL faltante en producción"
    exit 1
  fi
fi

echo "🔧 Migrando/Inicializando base de datos si es necesario"
python - <<'PY'
import os
from pathlib import Path
from app import app, db
with app.app_context():
    db.create_all()
print("✅ Base de datos lista")
PY

echo "🌐 Lanzando Gunicorn en puerto ${PORT}"
exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 --keep-alive 5 belgrano_tickets.wsgi:app

#!/bin/bash
# Script de inicio para la Ticketera
# Inicializa la base de datos de forma segura y arranca el servidor Gunicorn

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
    echo "Inicializando base de datos..."
    
    # Verificar que el script de inicialización existe
    SCRIPT_PATH=""
    
    # Mostrar información de debug
    echo "🔍 Información de debug:"
    echo "   Directorio actual: $(pwd)"
    echo "   Usuario actual: $(whoami)"
    echo "   Contenido del directorio actual:"
    ls -la | head -10
    
    # Posibles ubicaciones del script (en orden de prioridad)
    POSSIBLE_PATHS=(
        "scripts/init_users_flota.py"
        "./scripts/init_users_flota.py"
        "/app/scripts/init_users_flota.py"
        "belgrano_tickets/scripts/init_users_flota.py"
        "./belgrano_tickets/scripts/init_users_flota.py"
        "./init_users_flota.py"
        "/app/init_users_flota.py"
    )
    
    for path in "${POSSIBLE_PATHS[@]}"; do
        if [ -f "$path" ]; then
            SCRIPT_PATH="$path"
            break
        fi
    done
    
    if [ -z "$SCRIPT_PATH" ]; then
        echo "❌ Buscando script en las siguientes ubicaciones:"
        for path in "${POSSIBLE_PATHS[@]}"; do
            echo "   - $path $([ -f "$path" ] && echo "✅ ENCONTRADO" || echo "❌ NO ENCONTRADO")"
        done
        echo "📁 Contenido del directorio actual:"
        ls -la
        echo "📁 Contenido del directorio scripts (si existe):"
        [ -d "scripts" ] && ls -la scripts/ || echo "   Directorio scripts no existe"
        handle_error "Script de inicialización no encontrado en ninguna ubicación"
    fi
    
    echo "📁 Script encontrado en: $SCRIPT_PATH"
    
    # Actualizar esquema de base de datos primero
    echo "🔧 Actualizando esquema de base de datos..."
    ACTUALIZAR_DB_PATH=""
    if [ -f "belgrano_tickets/actualizar_db.py" ]; then
        ACTUALIZAR_DB_PATH="belgrano_tickets/actualizar_db.py"
    elif [ -f "actualizar_db.py" ]; then
        ACTUALIZAR_DB_PATH="actualizar_db.py"
    else
        echo "Script actualizar_db.py no encontrado, saltando..."
        ACTUALIZAR_DB_PATH=""
    fi
    
    if [ -n "$ACTUALIZAR_DB_PATH" ]; then
        echo "📁 Actualizar DB encontrado en: $ACTUALIZAR_DB_PATH"
        if python3 "$ACTUALIZAR_DB_PATH"; then
            echo "✅ Esquema de base de datos actualizado"
        else
            echo "Error actualizando esquema, continuando..."
        fi
    fi
    
    # Ejecutar script de inicialización
    if python3 "$SCRIPT_PATH"; then
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
            echo "Variable de entorno $var no está definida"
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
    echo "   Workers: 2"
    echo "   Bind: 0.0.0.0:$PORT"
    echo "================================"
    
    # Comando Gunicorn con configuración
    exec gunicorn \
        --config gunicorn.conf.py \
        wsgi:application
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
