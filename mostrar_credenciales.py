#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para mostrar las credenciales de acceso de Belgrano Tickets
"""

import sqlite3
import os

def mostrar_credenciales():
    """Mostrar todas las credenciales de acceso"""
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
    
    if not os.path.exists(db_path):
        print("❌ Base de datos no encontrada")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, email, role, nombre FROM user ORDER BY role, username')
    usuarios = cursor.fetchall()
    
    print("🚀 CREDENCIALES DE ACCESO - BELGRANO TICKETS")
    print("=" * 70)
    print()
    
    # Separar usuarios por rol
    admin_users = [u for u in usuarios if u[2] == 'admin']
    flota_users = [u for u in usuarios if u[2] == 'flota']
    
    # Mostrar usuarios admin
    if admin_users:
        print("👨‍💼 USUARIOS ADMIN (Acceso completo):")
        print("-" * 50)
        for usuario in admin_users:
            print(f"   Email: {usuario[1]}")
            print(f"   Password: admin123")
            print(f"   Nombre: {usuario[3]}")
            print(f"   Role: {usuario[2]}")
            print()
    
    # Mostrar usuarios flota
    if flota_users:
        print("🚚 USUARIOS FLOTA (Acceso limitado):")
        print("-" * 50)
        for usuario in flota_users:
            print(f"   Email: {usuario[1]}")
            print(f"   Password: flota123")
            print(f"   Nombre: {usuario[3]}")
            print(f"   Role: {usuario[2]}")
            print()
    
    print("=" * 70)
    print("💡 INSTRUCCIONES DE ACCESO:")
    print("   1. Inicia la aplicación: python app.py")
    print("   2. Ve a: http://localhost:5001")
    print("   3. Usa cualquiera de las credenciales mostradas arriba")
    print()
    print("🔐 CONTRASEÑAS:")
    print("   - Admin: admin123")
    print("   - Flota: flota123")
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    mostrar_credenciales()
