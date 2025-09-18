#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar mejoras de seguridad a Belgrano Tickets
"""

import os
import sys

def apply_improvements():
    """Aplicar mejoras de seguridad y funcionalidad"""
    print("🔄 Aplicando mejoras a Belgrano Tickets...")
    
    try:
        # Importar la aplicación
        from app import app, db
        from models import User
        from hash_compat import resetear_credenciales_admin
        
        # Crear tablas si no existen
        db.create_all()
        print("✅ Base de datos inicializada")
        
        # Resetear credenciales
        if resetear_credenciales_admin():
            print("✅ Credenciales reseteadas")
        else:
            print("❌ Error reseteando credenciales")
            return False
        
        # Verificar usuarios
        usuarios = User.query.all()
        print(f"📋 Usuarios en la base de datos: {len(usuarios)}")
        for user in usuarios:
            print(f"   • {user.email} ({user.rol}) - {'✅ Activo' if user.activo else '❌ Inactivo'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error aplicando mejoras: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if apply_improvements():
        print("✅ Mejoras aplicadas exitosamente")
        print()
        print("🔐 Credenciales disponibles:")
        print("   • Admin: admin@belgranoahorro.com / admin123")
        print("   • Flota: repartidor1@belgranoahorro.com / flota123")
    else:
        print("❌ Error aplicando mejoras")
        sys.exit(1)
