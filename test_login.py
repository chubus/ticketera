#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el sistema de login
"""

import requests
import json
import time

def test_login_system():
    """Probar el sistema de login"""
    base_url = "http://localhost:5001"
    
    print("🧪 PRUEBA DEL SISTEMA DE LOGIN - BELGRANO TICKETS")
    print("=" * 60)
    
    # Verificar que el servidor esté corriendo
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print("✅ Servidor respondiendo correctamente")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("💡 Asegúrate de que el servidor esté corriendo con: python app.py")
        return False
    
    # Verificar credenciales de debug
    try:
        response = requests.get(f"{base_url}/debug/credenciales", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Credenciales de debug disponibles")
            print(f"   Total usuarios: {data['total_usuarios']}")
            print(f"   Admin: {data['credenciales_admin']['email']}")
            print(f"   Flota: {data['credenciales_flota']['email']}")
        else:
            print(f"⚠️ Ruta de debug no disponible (status: {response.status_code})")
    except Exception as e:
        print(f"⚠️ Error accediendo a debug: {e}")
    
    # Probar login con credenciales correctas
    print("\n🔐 PROBANDO LOGIN CON CREDENCIALES CORRECTAS...")
    
    # Test admin
    admin_credentials = {
        'email': 'admin@belgranoahorro.com',
        'password': 'admin123'
    }
    
    try:
        session = requests.Session()
        response = session.post(f"{base_url}/login", data=admin_credentials, timeout=10)
        
        if response.status_code == 200:
            if 'panel' in response.url or 'panel' in response.text:
                print("✅ Login de admin exitoso")
            else:
                print("⚠️ Login de admin - verificar redirección")
        else:
            print(f"❌ Login de admin falló (status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ Error en login de admin: {e}")
    
    # Test flota
    flota_credentials = {
        'email': 'repartidor1@belgranoahorro.com',
        'password': 'flota123'
    }
    
    try:
        session = requests.Session()
        response = session.post(f"{base_url}/login", data=flota_credentials, timeout=10)
        
        if response.status_code == 200:
            if 'panel' in response.url or 'panel' in response.text:
                print("✅ Login de flota exitoso")
            else:
                print("⚠️ Login de flota - verificar redirección")
        else:
            print(f"❌ Login de flota falló (status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ Error en login de flota: {e}")
    
    # Probar login con credenciales incorrectas
    print("\n❌ PROBANDO LOGIN CON CREDENCIALES INCORRECTAS...")
    
    wrong_credentials = {
        'email': 'admin@belgranoahorro.com',
        'password': 'password_incorrecta'
    }
    
    try:
        session = requests.Session()
        response = session.post(f"{base_url}/login", data=wrong_credentials, timeout=10)
        
        if response.status_code == 200:
            if 'incorrectos' in response.text or 'incorrecta' in response.text:
                print("✅ Rechazo de credenciales incorrectas funcionando")
            else:
                print("⚠️ Verificar mensaje de error para credenciales incorrectas")
        else:
            print(f"⚠️ Status inesperado para credenciales incorrectas: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error probando credenciales incorrectas: {e}")
    
    print("\n🎯 RESUMEN DE PRUEBAS:")
    print("   • Verifica que puedas acceder a http://localhost:5001")
    print("   • Usa las credenciales mostradas en la página de login")
    print("   • Admin: admin@belgranoahorro.com / admin123")
    print("   • Flota: repartidor1@belgranoahorro.com / flota123")
    
    return True

if __name__ == "__main__":
    test_login_system()
