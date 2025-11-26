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

