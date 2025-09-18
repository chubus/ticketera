#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que las credenciales funcionen correctamente
"""

import os
import sys
import sqlite3
from werkzeug.security import check_password_hash

def verificar_credenciales():
    """Verificar que las credenciales funcionen correctamente"""
    print("🔍 Verificando credenciales de la ticketera...")
    
    # Ruta de la base de datos
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    
    if not os.path.exists(db_path):
        print("❌ Base de datos no encontrada")
        return False
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar usuarios
    cursor.execute('SELECT username, email, password, role, nombre, activo FROM user')
    usuarios = cursor.fetchall()
    
    print(f"   Total de usuarios encontrados: {len(usuarios)}")
    
    # Credenciales de prueba
    credenciales_prueba = [
        ('admin@belgranoahorro.com', 'admin123', 'admin'),
        ('repartidor1@belgranoahorro.com', 'flota123', 'flota'),
        ('repartidor2@belgranoahorro.com', 'flota123', 'flota'),
        ('repartidor3@belgranoahorro.com', 'flota123', 'flota')
    ]
    
    credenciales_ok = 0
    credenciales_error = 0
    
    for email, password, role_esperado in credenciales_prueba:
        # Buscar usuario
        cursor.execute('SELECT password, role, activo FROM user WHERE email = ?', (email,))
        resultado = cursor.fetchone()
        
        if resultado:
            password_hash, role, activo = resultado
            
            # Verificar contraseña
            if check_password_hash(password_hash, password):
                if role == role_esperado and activo:
                    print(f"✅ {email} - Login correcto ({role})")
                    credenciales_ok += 1
                else:
                    print(f"❌ {email} - Role o estado incorrecto")
                    credenciales_error += 1
            else:
                print(f"❌ {email} - Contraseña incorrecta")
                credenciales_error += 1
        else:
            print(f"❌ {email} - Usuario no encontrado")
            credenciales_error += 1
    
    conn.close()
    
    print(f"\n📊 Resultados:")
    print(f"   ✅ Credenciales correctas: {credenciales_ok}")
    print(f"   ❌ Credenciales con error: {credenciales_error}")
    
    if credenciales_error == 0:
        print("\n🎉 Todas las credenciales funcionan correctamente!")
        return True
    else:
        print(f"\n⚠️ Hay {credenciales_error} credenciales con problemas")
        return False

if __name__ == "__main__":
    try:
        if verificar_credenciales():
            print("\n✅ Verificación exitosa - Las credenciales están listas para usar")
        else:
            print("\n❌ Verificación fallida - Revisar las credenciales")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        sys.exit(1)
