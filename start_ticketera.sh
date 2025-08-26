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
python -c "
import os
import sys
import sqlite3
import hashlib
import secrets

def generate_password_hash(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f'pbkdf2:sha256:100000\${salt}\${hash_obj.hex()}'

def crear_usuarios_iniciales():
    db_path = 'belgrano_tickets.db'
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla user si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL,
            role VARCHAR(20) NOT NULL,
            nombre VARCHAR(50)
        )
    ''')
    
    # Usuario Admin
    admin_password = generate_password_hash('admin123')
    try:
        cursor.execute('''
            INSERT INTO user (username, email, password, role, nombre)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin@belgranoahorro.com', admin_password, 'admin', 'Administrador Principal'))
        print('Usuario admin creado')
    except sqlite3.IntegrityError:
        print('Usuario admin ya existe')
    
    # Usuarios Flota
    usuarios_flota = [
        ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
        ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
        ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
        ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
        ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
    ]
    
    flota_password = generate_password_hash('flota123')
    
    for i, (username, email, nombre) in enumerate(usuarios_flota, 1):
        try:
            cursor.execute('''
                INSERT INTO user (username, email, password, role, nombre)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, flota_password, 'flota', nombre))
            print(f'Usuario flota{i} creado')
        except sqlite3.IntegrityError:
            print(f'Usuario flota{i} ya existe')
    
    # Guardar cambios
    conn.commit()
    conn.close()
    print('Usuarios inicializados correctamente')

try:
    from app import app, db
    with app.app_context():
        db.create_all()
        print('Base de datos de tickets inicializada exitosamente')
        crear_usuarios_iniciales()
except Exception as e:
    print(f'Error al inicializar base de datos: {e}')
    sys.exit(1)
"

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
echo "   Flota: repartidor1@belgranoahorro.com / flota123 (y otros 4 usuarios flota)"

# Iniciar la aplicacion
echo "Iniciando aplicacion en puerto $PORT..."
echo "La ticketera estara disponible en http://localhost:$PORT"

# Ejecutar la aplicacion con gunicorn para produccion
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
