#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para resetear credenciales de Belgrano Tickets
"""

import sqlite3
from werkzeug.security import generate_password_hash

def reset_credentials():
    """Resetear credenciales de admin y flota"""
    try:
        conn = sqlite3.connect('belgrano_tickets.db')
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print("❌ Tabla 'user' no encontrada")
            return False
        
        # Resetear admin
        admin_password = generate_password_hash('admin123')
        cursor.execute('''
            UPDATE user 
            SET password = ?, activo = 1 
            WHERE email = 'admin@belgranoahorro.com'
        ''', (admin_password,))
        
        # Si no existe admin, crearlo
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO user (username, email, password, nombre, rol, activo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@belgranoahorro.com', admin_password, 'Administrador', 'admin', 1))
            print("✅ Admin creado")
        else:
            print("✅ Admin actualizado")
        
        # Resetear usuarios flota
        flota_password = generate_password_hash('flota123')
        flota_usuarios = [
            ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
            ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
            ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
            ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
            ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
        ]
        
        for username, email, nombre in flota_usuarios:
            cursor.execute('''
                UPDATE user 
                SET password = ?, activo = 1 
                WHERE email = ?
            ''', (flota_password, email))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO user (username, email, password, nombre, rol, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, flota_password, nombre, 'flota', 1))
                print(f"✅ Flota creado: {email}")
            else:
                print(f"✅ Flota actualizado: {email}")
        
        # Verificar cambios
        cursor.execute('SELECT email, rol, activo FROM user WHERE rol IN ("admin", "flota")')
        users = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        print("✅ Credenciales reseteadas exitosamente:")
        print("   • Admin: admin@belgranoahorro.com / admin123")
        print("   • Flota: repartidor1@belgranoahorro.com / flota123")
        print()
        print("📋 Usuarios activos:")
        for email, rol, activo in users:
            status = "✅ Activo" if activo else "❌ Inactivo"
            print(f"   • {email} ({rol}) - {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reseteando credenciales: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Reseteando credenciales de Belgrano Tickets...")
    if reset_credentials():
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ Error en el proceso")
