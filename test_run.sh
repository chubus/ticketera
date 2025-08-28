#!/bin/bash
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el funcionamiento del run.sh
"""

echo "🧪 Probando script de inicio..."
echo "================================"

# Verificar que el script existe
if [ ! -f "run.sh" ]; then
    echo "❌ Error: run.sh no encontrado"
    exit 1
fi

# Verificar que el script de inicialización existe
if [ ! -f "scripts/init_users_flota.py" ]; then
    echo "❌ Error: scripts/init_users_flota.py no encontrado"
    exit 1
fi

# Verificar que wsgi.py existe
if [ ! -f "wsgi.py" ]; then
    echo "❌ Error: wsgi.py no encontrado"
    exit 1
fi

# Verificar dependencias
echo "🔍 Verificando dependencias..."
python3 -c "import gunicorn; print('✅ Gunicorn disponible')"
python3 -c "import gevent; print('✅ Gevent disponible')"
python3 -c "import flask; print('✅ Flask disponible')"

echo "✅ Todas las verificaciones pasaron"
echo "🚀 El script run.sh está listo para usar"
