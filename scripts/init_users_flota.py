#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización segura de usuarios para la Ticketera
Garantiza que los usuarios no se dupliquen al crearlos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_users_safely():
    """Inicializar usuarios de forma segura sin duplicados"""
    with app.app_context():
        try:
            print("🔧 Inicializando base de datos...")
            db.create_all()
            print("✅ Base de datos creada/verificada")
            
            # Verificar si ya existen usuarios
            total_users = User.query.count()
            print(f"📊 Usuarios existentes en BD: {total_users}")
            
            if total_users > 0:
                print("ℹ️ Usuarios ya existen, saltando inicialización")
                return True
            
            print("👥 Creando usuarios iniciales...")
            
            # Usuario Admin
            admin_email = 'admin@belgranoahorro.com'
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(
                    username='admin',
                    email=admin_email,
                    password=generate_password_hash('admin123'),
                    role='admin',
                    nombre='Administrador Principal',
                    activo=True
                )
                db.session.add(admin)
                print("✅ Usuario admin creado: admin@belgranoahorro.com / admin123")
            else:
                print("ℹ️ Usuario admin ya existe")
            
            # Usuarios Flota
            flota_usuarios = [
                ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
                ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
                ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
                ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
                ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
            ]
            
            for username, email, nombre in flota_usuarios:
                existing_user = User.query.filter_by(email=email).first()
                if not existing_user:
                    flota = User(
                        username=username,
                        email=email,
                        password=generate_password_hash('flota123'),
                        role='flota',
                        nombre=nombre,
                        activo=True
                    )
                    db.session.add(flota)
                    print(f"✅ Usuario flota creado: {email} / flota123")
                else:
                    print(f"ℹ️ Usuario flota ya existe: {email}")
            
            # Commit de todos los cambios
            db.session.commit()
            print("✅ Todos los usuarios inicializados correctamente")
            
            # Verificar usuarios creados
            total_users = User.query.count()
            print(f"📊 Total de usuarios en BD: {total_users}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando usuarios: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = init_users_safely()
    if success:
        print("🎉 Inicialización completada exitosamente")
        sys.exit(0)
    else:
        print("💥 Error en la inicialización")
        sys.exit(1)
