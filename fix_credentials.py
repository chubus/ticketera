#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para arreglar credenciales de Belgrano Tickets
"""

import sqlite3
from werkzeug.security import generate_password_hash

def fix_credentials():
    """Arreglar credenciales de admin y flota"""
    try:
        conn = sqlite3.connect('belgrano_tickets.db')
        cursor = conn.cursor()
        
        # Verificar estructura de la tabla
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        print("📋 Estructura de tabla 'user':")
        for col in columns:
            print(f"   • {col[1]} ({col[2]})")
        
        # Verificar usuarios existentes
        cursor.execute("SELECT * FROM user LIMIT 5")
        users = cursor.fetchall()
        print(f"\n📋 Usuarios existentes: {len(users)}")
        for user in users:
            print(f"   • {user}")
        
        # Resetear admin
        admin_password = generate_password_hash('admin123')
        
        # Intentar actualizar admin
        cursor.execute('''
            UPDATE user 
            SET password = ?, activo = 1 
            WHERE email = 'admin@belgranoahorro.com'
        ''', (admin_password,))
        
        if cursor.rowcount == 0:
            # Crear admin si no existe
            cursor.execute('''
                INSERT INTO user (username, email, password, nombre, role, activo)
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
                    INSERT INTO user (username, email, password, nombre, role, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, flota_password, nombre, 'flota', 1))
                print(f"✅ Flota creado: {email}")
            else:
                print(f"✅ Flota actualizado: {email}")
        
        # Verificar cambios finales
        cursor.execute('SELECT email, role, activo FROM user WHERE role IN ("admin", "flota")')
        final_users = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        print("\n✅ Credenciales arregladas exitosamente:")
        print("   • Admin: admin@belgranoahorro.com / admin123")
        print("   • Flota: repartidor1@belgranoahorro.com / flota123")
        print()
        print("📋 Usuarios finales:")
        for email, role, activo in final_users:
            status = "✅ Activo" if activo else "❌ Inactivo"
            print(f"   • {email} ({role}) - {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error arreglando credenciales: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔄 Arreglando credenciales de Belgrano Tickets...")
    if fix_credentials():
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ Error en el proceso")
