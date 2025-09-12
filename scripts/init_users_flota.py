#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización de usuarios para la flota
Este script se ejecuta durante el deploy para inicializar usuarios básicos
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

def init_database():
    """Inicializar la base de datos si no existe"""
    try:
        # Crear directorio si no existe
        os.makedirs('data', exist_ok=True)
        
        # Determinar la ruta de la base de datos
        db_path = 'data/belgrano_ahorro.db'
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tabla de usuarios si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'usuario',
                activo BOOLEAN DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Crear tabla de flota si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flota (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                activo BOOLEAN DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Base de datos inicializada correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        return False

def create_default_users():
    """Crear usuarios por defecto"""
    try:
        conn = sqlite3.connect('data/belgrano_ahorro.db')
        cursor = conn.cursor()
            
            # Verificar si ya existen usuarios
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"✅ Ya existen {count} usuarios en la base de datos")
            conn.close()
            return True
        
        # Crear usuarios por defecto
        default_users = [
            {
                'username': 'admin',
                'email': 'admin@belgranoahorro.com',
                'password_hash': 'admin_hash_2025',  # En producción usar hash real
                'rol': 'admin'
            },
            {
                'username': 'flota_manager',
                'email': 'flota@belgranoahorro.com',
                'password_hash': 'flota_hash_2025',  # En producción usar hash real
                'rol': 'flota_manager'
            },
            {
                'username': 'operador',
                'email': 'operador@belgranoahorro.com',
                'password_hash': 'operador_hash_2025',  # En producción usar hash real
                'rol': 'operador'
            }
        ]
        
        for user in default_users:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, email, password_hash, rol)
                VALUES (?, ?, ?, ?)
            ''', (user['username'], user['email'], user['password_hash'], user['rol']))
        
        conn.commit()
        print(f"✅ Creados {len(default_users)} usuarios por defecto")
        
        conn.close()
                return True
            
    except Exception as e:
        print(f"❌ Error creando usuarios por defecto: {e}")
        return False

def create_default_flota():
    """Crear datos de flota por defecto"""
    try:
        conn = sqlite3.connect('data/belgrano_ahorro.db')
        cursor = conn.cursor()
        
        # Verificar si ya existe flota
        cursor.execute("SELECT COUNT(*) FROM flota")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"✅ Ya existen {count} registros de flota")
            conn.close()
            return True
        
        # Crear flota por defecto
        default_flota = [
            {
                'nombre': 'Flota Principal',
                'descripcion': 'Flota principal de Belgrano Ahorro'
            },
            {
                'nombre': 'Flota Secundaria',
                'descripcion': 'Flota secundaria para operaciones especiales'
            }
        ]
        
        for flota in default_flota:
            cursor.execute('''
                INSERT OR IGNORE INTO flota (nombre, descripcion)
                VALUES (?, ?)
            ''', (flota['nombre'], flota['descripcion']))
        
        conn.commit()
        print(f"✅ Creados {len(default_flota)} registros de flota")
        
        conn.close()
            return True
            
        except Exception as e:
        print(f"❌ Error creando datos de flota: {e}")
            return False

def main():
    """Función principal"""
    print("🚀 Inicializando usuarios y flota...")
    print("=" * 40)
    
    try:
        # Cambiar al directorio del script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        
        # Si estamos en un subdirectorio, cambiar al directorio padre
        if os.path.basename(script_dir) == 'scripts':
            os.chdir(project_dir)
        
        print(f"📁 Directorio de trabajo: {os.getcwd()}")
        print(f"📁 Script ubicado en: {script_dir}")
        
        # Inicializar base de datos
        if not init_database():
            print("❌ Error inicializando base de datos")
            sys.exit(1)
        
        # Crear usuarios por defecto
        if not create_default_users():
            print("❌ Error creando usuarios por defecto")
        sys.exit(1)

        # Crear datos de flota por defecto
        if not create_default_flota():
            print("❌ Error creando datos de flota")
        sys.exit(1)

        print("=" * 40)
        print("✅ Inicialización completada exitosamente")
        print(f"🕐 Timestamp: {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"❌ Error en función main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()