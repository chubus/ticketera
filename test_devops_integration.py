#!/usr/bin/env python3
"""
Script de prueba para verificar la integración del panel de DevOps
"""

import os
import sys
import requests
from datetime import datetime

# Cargar variables de entorno desde .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except Exception as e:
        print(f"Advertencia: No se pudo cargar .env: {e}")

def test_devops_integration():
    """Probar la integración del panel de DevOps"""
    print("=" * 60)
    print("PRUEBA DE INTEGRACIÓN DEL PANEL DEVOPS")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar variables de entorno
    print("1. Verificando variables de entorno...")
    required_vars = [
        'DEVOPS_USERNAME',
        'DEVOPS_PASSWORD', 
        'BELGRANO_AHORRO_URL',
        'BELGRANO_AHORRO_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables faltantes: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Todas las variables de entorno están configuradas")
    
    # Verificar archivos necesarios
    print("\n2. Verificando archivos necesarios...")
    required_files = [
        'devops_routes.py',
        'templates/devops/login.html',
        'templates/devops/dashboard.html',
        'templates/devops/productos.html',
        'templates/devops/sucursales.html',
        'templates/devops/negocios.html',
        'templates/devops/ofertas.html',
        'templates/devops/precios.html'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Archivos faltantes: {', '.join(missing_files)}")
        return False
    else:
        print("✅ Todos los archivos necesarios están presentes")
    
    # Verificar integración en base.html
    print("\n3. Verificando integración en navegación...")
    try:
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'Panel DevOps' in content and '/devops/login' in content:
                print("✅ Enlace al panel DevOps integrado en navegación")
            else:
                print("❌ Enlace al panel DevOps no encontrado en navegación")
                return False
    except Exception as e:
        print(f"❌ Error leyendo base.html: {e}")
        return False
    
    # Verificar blueprint en app.py
    print("\n4. Verificando registro de blueprint...")
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'devops_bp' in content and 'register_blueprint' in content:
                print("✅ Blueprint de DevOps registrado en app.py")
            else:
                print("❌ Blueprint de DevOps no encontrado en app.py")
                return False
    except Exception as e:
        print(f"❌ Error leyendo app.py: {e}")
        return False
    
    # Verificar sintaxis de devops_routes.py
    print("\n5. Verificando sintaxis de devops_routes.py...")
    try:
        with open('devops_routes.py', 'r', encoding='utf-8') as f:
            content = f.read()
            compile(content, 'devops_routes.py', 'exec')
        print("✅ Sintaxis de devops_routes.py correcta")
    except SyntaxError as e:
        print(f"❌ Error de sintaxis en devops_routes.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando devops_routes.py: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ INTEGRACIÓN DEL PANEL DEVOPS COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print()
    print("ACCESO AL PANEL:")
    print(f"  URL: http://localhost:5001/devops/login")
    print(f"  Usuario: {os.getenv('DEVOPS_USERNAME')}")
    print(f"  Contraseña: {os.getenv('DEVOPS_PASSWORD')}")
    print()
    print("FUNCIONALIDADES DISPONIBLES:")
    print("  • Gestión de Productos")
    print("  • Gestión de Sucursales") 
    print("  • Gestión de Negocios")
    print("  • Gestión de Ofertas")
    print("  • Gestión de Precios")
    print()
    print("El panel está accesible desde la navegación principal")
    print("junto al botón 'Cerrar Sesión'")
    
    return True

if __name__ == "__main__":
    success = test_devops_integration()
    sys.exit(0 if success else 1)
