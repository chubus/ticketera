#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar credenciales de administrador
"""

import os
import sys
from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

def crear_app():
    """Crear aplicación Flask para diagnóstico"""
    app = Flask(__name__)
    
    # Configuración de base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    print(f"🗄️ Ruta de base de datos: {db_path}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'
    
    # Inicializar extensiones
    db.init_app(app)
    
    return app

def diagnosticar_admin():
    """Diagnosticar el estado de las credenciales de administrador"""
    app = crear_app()
    
    with app.app_context():
        try:
            print("🔍 DIAGNÓSTICO DE CREDENCIALES ADMIN")
            print("=" * 50)
            
            # Verificar si existe la base de datos
            if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')):
                print("❌ Base de datos no encontrada")
                return False
            
            # Verificar usuarios existentes
            usuarios = User.query.all()
            print(f"📊 Total de usuarios: {len(usuarios)}")
            
            if len(usuarios) == 0:
                print("❌ No hay usuarios en la base de datos")
                return False
            
            # Buscar usuario admin
            admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
            
            if not admin:
                print("❌ Usuario admin no encontrado")
                print("👥 Usuarios existentes:")
                for user in usuarios:
                    print(f"   - {user.email} ({user.role})")
                return False
            
            print(f"✅ Usuario admin encontrado: {admin.nombre}")
            print(f"   Email: {admin.email}")
            print(f"   Role: {admin.role}")
            print(f"   Password hash: {admin.password[:50]}...")
            
            # Verificar contraseña
            password_correcto = check_password_hash(admin.password, 'admin123')
            print(f"🔐 Verificación de contraseña 'admin123': {'✅ CORRECTO' if password_correcto else '❌ INCORRECTO'}")
            
            if not password_correcto:
                print("🔧 Intentando regenerar contraseña...")
                admin.password = generate_password_hash('admin123')
                db.session.commit()
                
                # Verificar nuevamente
                password_correcto = check_password_hash(admin.password, 'admin123')
                print(f"🔐 Verificación después de regenerar: {'✅ CORRECTO' if password_correcto else '❌ INCORRECTO'}")
            
            # Verificar otros usuarios
            print("\n👥 VERIFICACIÓN DE OTROS USUARIOS:")
            for user in usuarios:
                if user.email != 'admin@belgranoahorro.com':
                    if user.role == 'flota':
                        password_test = 'flota123'
                    else:
                        password_test = 'admin123'
                    
                    password_ok = check_password_hash(user.password, password_test)
                    print(f"   {user.email} ({user.role}): {'✅' if password_ok else '❌'}")
            
            return password_correcto
            
        except Exception as e:
            print(f"❌ Error en diagnóstico: {e}")
            return False

def crear_admin_manual():
    """Crear usuario admin manualmente si no existe"""
    app = crear_app()
    
    with app.app_context():
        try:
            print("\n🔧 CREANDO ADMIN MANUALMENTE...")
            
            # Verificar si ya existe
            admin_existente = User.query.filter_by(email='admin@belgranoahorro.com').first()
            if admin_existente:
                print("✅ Admin ya existe, actualizando contraseña...")
                admin_existente.password = generate_password_hash('admin123')
                db.session.commit()
                return True
            
            # Crear nuevo admin
            nuevo_admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                role='admin',
                nombre='Administrador Principal',
                activo=True
            )
            
            db.session.add(nuevo_admin)
            db.session.commit()
            
            print("✅ Admin creado exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error creando admin: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 DIAGNÓSTICO DE CREDENCIALES - BELGRANO TICKETS")
    print("=" * 60)
    
    # Ejecutar diagnóstico
    admin_ok = diagnosticar_admin()
    
    if not admin_ok:
        print("\n🔧 Intentando reparar credenciales...")
        reparado = crear_admin_manual()
        
        if reparado:
            print("\n🔍 Verificando reparación...")
            admin_ok = diagnosticar_admin()
    
    if admin_ok:
        print("\n✅ DIAGNÓSTICO COMPLETADO - CREDENCIALES FUNCIONANDO")
        print("🔐 Credenciales de acceso:")
        print("   Email: admin@belgranoahorro.com")
        print("   Password: admin123")
    else:
        print("\n❌ DIAGNÓSTICO FALLIDO - REVISAR BASE DE DATOS")
        sys.exit(1)
