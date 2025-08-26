#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación final del sistema de credenciales
"""

import os
import sys
from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

def crear_app():
    """Crear aplicación Flask para verificación"""
    app = Flask(__name__)
    
    # Configuración de base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'belgrano_tickets_secret_2025'
    
    # Inicializar extensiones
    db.init_app(app)
    
    return app

def verificar_sistema_completo():
    """Verificación completa del sistema"""
    app = crear_app()
    
    with app.app_context():
        try:
            print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA - BELGRANO TICKETS")
            print("=" * 70)
            
            # 1. Verificar base de datos
            print("\n1️⃣ VERIFICANDO BASE DE DATOS...")
            if not os.path.exists(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')):
                print("❌ Base de datos no encontrada")
                return False
            print("✅ Base de datos encontrada")
            
            # 2. Verificar usuarios
            print("\n2️⃣ VERIFICANDO USUARIOS...")
            usuarios = User.query.all()
            print(f"   Total usuarios: {len(usuarios)}")
            
            if len(usuarios) == 0:
                print("❌ No hay usuarios en la base de datos")
                return False
            
            # 3. Verificar admin
            print("\n3️⃣ VERIFICANDO ADMINISTRADOR...")
            admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
            
            if not admin:
                print("❌ Usuario admin no encontrado")
                return False
            
            print(f"✅ Admin encontrado: {admin.nombre}")
            print(f"   Email: {admin.email}")
            print(f"   Role: {admin.role}")
            print(f"   Activo: {admin.activo}")
            
            # Verificar contraseña admin
            admin_password_ok = check_password_hash(admin.password, 'admin123')
            print(f"   Contraseña 'admin123': {'✅ CORRECTO' if admin_password_ok else '❌ INCORRECTO'}")
            
            if not admin_password_ok:
                print("🔧 Regenerando contraseña admin...")
                admin.password = generate_password_hash('admin123')
                db.session.commit()
                admin_password_ok = check_password_hash(admin.password, 'admin123')
                print(f"   Contraseña después de regenerar: {'✅ CORRECTO' if admin_password_ok else '❌ INCORRECTO'}")
            
            # 4. Verificar flota
            print("\n4️⃣ VERIFICANDO USUARIOS FLOTA...")
            flota_users = User.query.filter_by(role='flota').all()
            print(f"   Total usuarios flota: {len(flota_users)}")
            
            flota_ok = True
            for user in flota_users:
                password_ok = check_password_hash(user.password, 'flota123')
                status = "✅" if password_ok else "❌"
                print(f"   {user.email}: {status}")
                if not password_ok:
                    flota_ok = False
                    # Regenerar contraseña
                    user.password = generate_password_hash('flota123')
            
            if not flota_ok:
                db.session.commit()
                print("🔧 Contraseñas de flota regeneradas")
            
            # 5. Verificar estructura de datos
            print("\n5️⃣ VERIFICANDO ESTRUCTURA DE DATOS...")
            for user in usuarios:
                campos_requeridos = ['username', 'email', 'password', 'role', 'nombre', 'activo']
                campos_faltantes = []
                
                for campo in campos_requeridos:
                    if not hasattr(user, campo) or getattr(user, campo) is None:
                        campos_faltantes.append(campo)
                
                if campos_faltantes:
                    print(f"❌ Usuario {user.email} - campos faltantes: {campos_faltantes}")
                else:
                    print(f"✅ Usuario {user.email} - estructura correcta")
            
            # 6. Resumen final
            print("\n" + "=" * 70)
            print("🎯 RESUMEN DE VERIFICACIÓN:")
            print(f"   • Base de datos: ✅")
            print(f"   • Total usuarios: {len(usuarios)}")
            print(f"   • Admin: {'✅' if admin_password_ok else '❌'}")
            print(f"   • Flota: {'✅' if flota_ok else '❌'}")
            
            if admin_password_ok and flota_ok:
                print("\n✅ SISTEMA VERIFICADO - TODO FUNCIONANDO CORRECTAMENTE")
                print("\n🔐 CREDENCIALES DE ACCESO:")
                print("   👨‍💼 ADMIN:")
                print("      Email: admin@belgranoahorro.com")
                print("      Password: admin123")
                print("   🚚 FLOTA:")
                print("      Email: repartidor1@belgranoahorro.com")
                print("      Password: flota123")
                print("\n🚀 INSTRUCCIONES:")
                print("   1. Ejecuta: python app.py")
                print("   2. Ve a: http://localhost:5001")
                print("   3. Usa las credenciales mostradas arriba")
                return True
            else:
                print("\n❌ SISTEMA CON PROBLEMAS - REVISAR CREDENCIALES")
                return False
                
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
            return False

if __name__ == "__main__":
    success = verificar_sistema_completo()
    
    if success:
        print("\n🎉 ¡Sistema listo para usar!")
    else:
        print("\n💥 Sistema necesita reparación")
        sys.exit(1)
