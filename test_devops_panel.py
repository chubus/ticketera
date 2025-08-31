#!/usr/bin/env python3
"""
Script de prueba para el Panel de DevOps
Verifica que todas las funcionalidades estén operativas
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
DEVOPS_URL = f"{BASE_URL}/devops"
DEVOPS_CREDENTIALS = {
    'username': 'devops',
    'password': 'devops2025'
}

def print_status(message, status="INFO"):
    """Imprimir mensaje con formato de estado"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "SUCCESS":
        print(f"[{timestamp}] ✅ {message}")
    elif status == "ERROR":
        print(f"[{timestamp}] ❌ {message}")
    elif status == "WARNING":
        print(f"[{timestamp}] ⚠️  {message}")
    else:
        print(f"[{timestamp}] ℹ️  {message}")

def test_server_connection():
    """Probar conexión con el servidor"""
    print_status("Probando conexión con el servidor...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            print_status("Servidor respondiendo correctamente", "SUCCESS")
            return True
        else:
            print_status(f"Servidor respondió con código {response.status_code}", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        print_status(f"Error de conexión: {e}", "ERROR")
        return False

def test_devops_login():
    """Probar login de DevOps"""
    print_status("Probando login de DevOps...")
    try:
        # Obtener la página de login
        response = requests.get(f"{DEVOPS_URL}/login")
        if response.status_code != 200:
            print_status("No se pudo acceder a la página de login", "ERROR")
            return False
        
        # Intentar login
        session = requests.Session()
        login_response = session.post(
            f"{DEVOPS_URL}/login",
            data=DEVOPS_CREDENTIALS,
            allow_redirects=False
        )
        
        if login_response.status_code == 302:  # Redirect después del login exitoso
            print_status("Login de DevOps exitoso", "SUCCESS")
            return session
        else:
            print_status("Login de DevOps falló", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Error en login: {e}", "ERROR")
        return False

def test_dashboard_access(session):
    """Probar acceso al dashboard"""
    print_status("Probando acceso al dashboard...")
    try:
        response = session.get(f"{DEVOPS_URL}/dashboard")
        if response.status_code == 200:
            print_status("Dashboard accesible", "SUCCESS")
            return True
        else:
            print_status(f"Dashboard no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo al dashboard: {e}", "ERROR")
        return False

def test_productos_page(session):
    """Probar página de productos"""
    print_status("Probando página de productos...")
    try:
        response = session.get(f"{DEVOPS_URL}/productos")
        if response.status_code == 200:
            print_status("Página de productos accesible", "SUCCESS")
            return True
        else:
            print_status(f"Página de productos no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo a productos: {e}", "ERROR")
        return False

def test_sucursales_page(session):
    """Probar página de sucursales"""
    print_status("Probando página de sucursales...")
    try:
        response = session.get(f"{DEVOPS_URL}/sucursales")
        if response.status_code == 200:
            print_status("Página de sucursales accesible", "SUCCESS")
            return True
        else:
            print_status(f"Página de sucursales no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo a sucursales: {e}", "ERROR")
        return False

def test_negocios_page(session):
    """Probar página de negocios"""
    print_status("Probando página de negocios...")
    try:
        response = session.get(f"{DEVOPS_URL}/negocios")
        if response.status_code == 200:
            print_status("Página de negocios accesible", "SUCCESS")
            return True
        else:
            print_status(f"Página de negocios no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo a negocios: {e}", "ERROR")
        return False

def test_ofertas_page(session):
    """Probar página de ofertas"""
    print_status("Probando página de ofertas...")
    try:
        response = session.get(f"{DEVOPS_URL}/ofertas")
        if response.status_code == 200:
            print_status("Página de ofertas accesible", "SUCCESS")
            return True
        else:
            print_status(f"Página de ofertas no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo a ofertas: {e}", "ERROR")
        return False

def test_precios_page(session):
    """Probar página de precios"""
    print_status("Probando página de precios...")
    try:
        response = session.get(f"{DEVOPS_URL}/precios")
        if response.status_code == 200:
            print_status("Página de precios accesible", "SUCCESS")
            return True
        else:
            print_status(f"Página de precios no accesible: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error accediendo a precios: {e}", "ERROR")
        return False

def test_logout(session):
    """Probar logout"""
    print_status("Probando logout...")
    try:
        response = session.get(f"{DEVOPS_URL}/logout", allow_redirects=False)
        if response.status_code == 302:  # Redirect después del logout
            print_status("Logout exitoso", "SUCCESS")
            return True
        else:
            print_status(f"Logout falló: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error en logout: {e}", "ERROR")
        return False

def test_api_communication():
    """Probar comunicación con API de Belgrano Ahorro"""
    print_status("Probando comunicación con API de Belgrano Ahorro...")
    try:
        # Intentar obtener estadísticas
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print_status("API de Belgrano Ahorro respondiendo", "SUCCESS")
            print_status(f"Estadísticas obtenidas: {stats}")
            return True
        else:
            print_status(f"API respondió con código {response.status_code}", "WARNING")
            return False
    except Exception as e:
        print_status(f"Error comunicándose con API: {e}", "WARNING")
        return False

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("=" * 60)
    print("🧪 PRUEBAS DEL PANEL DE DEVOPS")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 8
    
    # Test 1: Conexión al servidor
    if test_server_connection():
        tests_passed += 1
    
    # Test 2: Login de DevOps
    session = test_devops_login()
    if session:
        tests_passed += 1
        
        # Test 3: Dashboard
        if test_dashboard_access(session):
            tests_passed += 1
        
        # Test 4: Página de productos
        if test_productos_page(session):
            tests_passed += 1
        
        # Test 5: Página de sucursales
        if test_sucursales_page(session):
            tests_passed += 1
        
        # Test 6: Página de negocios
        if test_negocios_page(session):
            tests_passed += 1
        
        # Test 7: Página de ofertas
        if test_ofertas_page(session):
            tests_passed += 1
        
        # Test 8: Página de precios
        if test_precios_page(session):
            tests_passed += 1
        
        # Test 9: Logout
        if test_logout(session):
            tests_passed += 1
    
    # Test adicional: Comunicación con API
    test_api_communication()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"Pruebas exitosas: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print_status("¡Todas las pruebas pasaron exitosamente!", "SUCCESS")
        print_status("El panel de DevOps está funcionando correctamente", "SUCCESS")
        return True
    else:
        print_status(f"Fallaron {total_tests - tests_passed} pruebas", "ERROR")
        print_status("Revisar los errores anteriores", "ERROR")
        return False

def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Script de prueba para el Panel de DevOps

Uso:
    python test_devops_panel.py          # Ejecutar todas las pruebas
    python test_devops_panel.py --help   # Mostrar esta ayuda

Pruebas incluidas:
    - Conexión al servidor
    - Login de DevOps
    - Acceso al dashboard
    - Acceso a todas las páginas de gestión
    - Logout
    - Comunicación con API de Belgrano Ahorro

Requisitos:
    - Servidor Flask ejecutándose en localhost:5000
    - Credenciales DevOps configuradas
    - API de Belgrano Ahorro disponible
        """)
        return
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
