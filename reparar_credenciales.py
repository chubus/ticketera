#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reparar credenciales en producción
"""

import os
import sys
from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

def crear_app():
    """Crear aplicación Flask para reparación"""
    app = Flask(__name__)
    
    # Configuración de base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'
    
    # Inicializar extensiones
    db.init_app(app)
    
    return app

def reparar_credenciales():
    """Reparar credenciales en producción"""
    app = crear_app()
    
    with app.app_context():
        try:
            print("🔧 REPARANDO CREDENCIALES EN PRODUCCIÓN")
            print("=" * 60)
            
            # Verificar si existe la base de datos
            if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')):
                print("❌ Base de datos no encontrada")
                return False
            
            # Crear tablas si no existen
            db.create_all()
            
            # Verificar usuarios existentes
            usuarios = User.query.all()
            print(f"📊 Usuarios existentes: {len(usuarios)}")
            
            # Buscar o crear usuario admin
            admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
            
            if admin:
                print("✅ Usuario admin encontrado, actualizando contraseña...")
                admin.password = generate_password_hash('admin123')
                admin.activo = True
                admin.role = 'admin'
                admin.nombre = 'Administrador Principal'
            else:
                print("🔧 Creando usuario admin...")
                admin = User(
                    username='admin',
                    email='admin@belgranoahorro.com',
                    password=generate_password_hash('admin123'),
                    role='admin',
                    nombre='Administrador Principal',
                    activo=True
                )
                db.session.add(admin)
            
            # Verificar usuarios flota
            flota_emails = [
                'repartidor1@belgranoahorro.com',
                'repartidor2@belgranoahorro.com',
                'repartidor3@belgranoahorro.com',
                'repartidor4@belgranoahorro.com',
                'repartidor5@belgranoahorro.com'
            ]
            
            flota_nombres = [
                'Repartidor 1',
                'Repartidor 2',
                'Repartidor 3',
                'Repartidor 4',
                'Repartidor 5'
            ]
            
            for i, email in enumerate(flota_emails):
                flota_user = User.query.filter_by(email=email).first()
                
                if flota_user:
                    print(f"✅ Usuario flota {i+1} encontrado, actualizando...")
                    flota_user.password = generate_password_hash('flota123')
                    flota_user.activo = True
                    flota_user.role = 'flota'
                    flota_user.nombre = flota_nombres[i]
                else:
                    print(f"🔧 Creando usuario flota {i+1}...")
                    flota_user = User(
                        username=f'repartidor{i+1}',
                        email=email,
                        password=generate_password_hash('flota123'),
                        role='flota',
                        nombre=flota_nombres[i],
                        activo=True
                    )
                    db.session.add(flota_user)
            
            # Guardar cambios
            db.session.commit()
            
            # Verificar que todo funcione
            print("\n🔍 VERIFICANDO CREDENCIALES...")
            
            admin_test = User.query.filter_by(email='admin@belgranoahorro.com').first()
            if admin_test and check_password_hash(admin_test.password, 'admin123'):
                print("✅ Credenciales de admin funcionando")
            else:
                print("❌ Error con credenciales de admin")
                return False
            
            flota_test = User.query.filter_by(email='repartidor1@belgranoahorro.com').first()
            if flota_test and check_password_hash(flota_test.password, 'flota123'):
                print("✅ Credenciales de flota funcionando")
            else:
                print("❌ Error con credenciales de flota")
                return False
            
            print("\n🎉 CREDENCIALES REPARADAS EXITOSAMENTE")
            print("🔐 Credenciales de acceso:")
            print("   Admin: admin@belgranoahorro.com / admin123")
            print("   Flota: repartidor1@belgranoahorro.com / flota123")
            
            return True
            
        except Exception as e:
            print(f"❌ Error reparando credenciales: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = reparar_credenciales()
    
    if success:
        print("\n✅ Reparación completada exitosamente")
    else:
        print("\n❌ Error en la reparación")
        sys.exit(1)
