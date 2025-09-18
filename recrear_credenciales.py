#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recrear todas las credenciales de la ticketera
"""

import os
import sys
import sqlite3
import hashlib
import secrets
from datetime import datetime

def generate_password_hash(password):
    """Generar hash de contraseña usando PBKDF2"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f'pbkdf2:sha256:100000${salt}${hash_obj.hex()}'

def recrear_credenciales():
    """Recrear todas las credenciales desde cero"""
    print("🔄 Recreando credenciales de la ticketera...")
    
    # Ruta de la base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    
    # Eliminar base de datos existente si existe
    if os.path.exists(db_path):
        print(f"   Eliminando base de datos existente: {db_path}")
        os.remove(db_path)
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla user
    cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL,
            role VARCHAR(20) NOT NULL,
            nombre VARCHAR(50),
            activo BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear tabla ticket
    cursor.execute('''
        CREATE TABLE ticket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ticket VARCHAR(20) UNIQUE NOT NULL,
            cliente VARCHAR(100) NOT NULL,
            productos TEXT NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            estado VARCHAR(20) DEFAULT 'pendiente',
            direccion TEXT,
            telefono VARCHAR(20),
            email VARCHAR(120),
            metodo_pago VARCHAR(50),
            notas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("   Tablas creadas correctamente")
    
    # Usuario Admin
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO user (username, email, password, role, nombre, activo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@belgranoahorro.com', admin_password, 'admin', 'Administrador Principal', 1))
    print('✅ Usuario admin creado: admin@belgranoahorro.com / admin123')
    
    # Usuarios Flota
    usuarios_flota = [
        ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
        ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
        ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
        ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
        ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5'),
        ('repartidor6', 'repartidor6@belgranoahorro.com', 'Repartidor 6'),
        ('repartidor7', 'repartidor7@belgranoahorro.com', 'Repartidor 7')
    ]
    
    flota_password = generate_password_hash('flota123')
    
    for i, (username, email, nombre) in enumerate(usuarios_flota, 1):
        cursor.execute('''
            INSERT INTO user (username, email, password, role, nombre, activo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, flota_password, 'flota', nombre, 1))
        print(f'✅ Usuario flota{i} creado: {email} / flota123')
    
    # Guardar cambios
    conn.commit()
    conn.close()
    
    print("\n🎉 Credenciales recreadas exitosamente!")
    print("\n📋 Credenciales disponibles:")
    print("   👑 Admin: admin@belgranoahorro.com / admin123")
    print("   🚚 Flota: repartidor1@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor2@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor3@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor4@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor5@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor6@belgranoahorro.com / flota123")
    print("   🚚 Flota: repartidor7@belgranoahorro.com / flota123")
    
    return True

if __name__ == "__main__":
    try:
        recrear_credenciales()
    except Exception as e:
        print(f"❌ Error al recrear credenciales: {e}")
        sys.exit(1)
