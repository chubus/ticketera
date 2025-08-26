#!/usr/bin/env python3
import os
import requests

def test_conexion():
    """Probar conexión con Belgrano Ahorro"""
    print("🔍 Probando conexión independiente...")
    
    belgrano_url = os.environ.get('BELGRANO_AHORRO_URL', 'http://localhost:5000')
    
    try:
        response = requests.get(f"{belgrano_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Conexión exitosa con Belgrano Ahorro")
            return True
        else:
            print(f"⚠️ Respuesta: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_conexion()
