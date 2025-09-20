#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que el deploy funcione correctamente
"""

import os
import sys
import traceback

def test_imports():
    """Probar todas las importaciones críticas"""
    print("🔍 Probando importaciones...")
    
    try:
        # Importar Flask
        from flask import Flask
        print("✅ Flask importado correctamente")
        
        # Importar SQLAlchemy
        from flask_sqlalchemy import SQLAlchemy
        print("✅ Flask-SQLAlchemy importado correctamente")
        
        # Importar Flask-Login
        from flask_login import LoginManager
        print("✅ Flask-Login importado correctamente")
        
        # Importar Flask-SocketIO
        from flask_socketio import SocketIO
        print("✅ Flask-SocketIO importado correctamente")
        
        # Importar modelos
        from models import db, User, Ticket
        print("✅ Modelos importados correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        traceback.print_exc()
        return False

def test_app_creation():
    """Probar la creación de la aplicación"""
    print("\n🔍 Probando creación de aplicación...")
    
    try:
        # Importar la aplicación
        from app import app
        print("✅ Aplicación importada correctamente")
        
        # Verificar configuración
        print(f"✅ Configuración SQLAlchemy: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        print(f"✅ Debug mode: {app.debug}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando aplicación: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Probar la base de datos"""
    print("\n🔍 Probando base de datos...")
    
    try:
        from app import app, db
        
        with app.app_context():
            # Verificar que las tablas existen
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Tablas encontradas: {tables}")
            
            # Verificar que podemos hacer una consulta simple
            from models import User
            user_count = User.query.count()
            print(f"✅ Usuarios en la base de datos: {user_count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error con base de datos: {e}")
        traceback.print_exc()
        return False

def test_wsgi():
    """Probar el punto de entrada WSGI"""
    print("\n🔍 Probando WSGI...")
    
    try:
        from wsgi import application
        print("✅ WSGI application importado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error con WSGI: {e}")
        traceback.print_exc()
        return False

def main():
    """Función principal de prueba"""
    print("🚀 PRUEBA DE DEPLOY - BELGRANO TICKETS")
    print("=" * 50)
    
    # Verificar variables de entorno
    print("🔍 Variables de entorno:")
    env_vars = [
        'FLASK_ENV', 'FLASK_APP', 'SECRET_KEY', 
        'DATABASE_URL', 'BELGRANO_AHORRO_URL'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'No configurada')
        print(f"  {var}: {value}")
    
    print("\n" + "=" * 50)
    
    # Ejecutar pruebas
    tests = [
        test_imports,
        test_app_creation,
        test_database,
        test_wsgi
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 RESULTADOS: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("✅ TODAS LAS PRUEBAS PASARON - DEPLOY LISTO")
        return 0
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON - REVISAR ERRORES")
        return 1

if __name__ == "__main__":
    sys.exit(main())

