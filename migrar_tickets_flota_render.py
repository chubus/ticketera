"""
Script de migración para Render - Asignar tickets a repartidores.

IMPORTANTE: Este script se ejecuta en Render a través de un comando one-off.

Uso en Render:
    Render Dashboard → Shell → python belgrano_tickets/migrar_tickets_flota_render.py
"""

import os
import sys

# Setup path
basedir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, basedir)

from models import db, Ticket, User
from app import app

def migrar_tickets_render():
    """
    Versión automatizada para Render (sin confirmación manual).
    """
    with app.app_context():
        print("\n" + "=" * 70)
        print("  MIGRACIÓN DE TICKETS - ASIGNACIÓN A REPARTIDORES (RENDER)")
        print("=" * 70 + "\n")
        
        # 1. Obtener usuarios de flota
        usuarios_flota = User.query.filter_by(role='flota', activo=True).all()
        
        if not usuarios_flota:
            print("❌ ERROR: No hay usuarios de flota activos")
            return False
        
        print(f"✅ {len(usuarios_flota)} usuarios de flota encontrados:\n")
        for user in usuarios_flota:
            print(f"   • {user.nombre} (ID: {user.id})")
        
        # 2. Crear mapeo
        nombre_a_id = {}
        for user in usuarios_flota:
            nombre_a_id[user.nombre] = user.id
            nombre_a_id[user.nombre.lower()] = user.id
            if hasattr(user, 'username'):
                nombre_a_id[user.username] = user.id
                nombre_a_id[user.username.lower()] = user.id
        
        # 3. Buscar tickets sin asignar
        tickets_sin_asignar = Ticket.query.filter(
            Ticket.repartidor_nombre.isnot(None),
            Ticket.asignado_a.is_(None)
        ).all()
        
        print(f"\n📦 {len(tickets_sin_asignar)} tickets necesitan migración\n")
        
        if not tickets_sin_asignar:
            print("✅ No hay tickets para migrar\n")
            return True
        
        # 4. Actualizar
        actualizados = 0
        no_mapeados = 0
        
        for ticket in tickets_sin_asignar:
            nombre = ticket.repartidor_nombre
            user_id = None
            
            # Intentar mapeo
            if nombre in nombre_a_id:
                user_id = nombre_a_id[nombre]
            elif nombre.lower() in nombre_a_id:
                user_id = nombre_a_id[nombre.lower()]
            else:
                # Buscar por similitud
                for user in usuarios_flota:
                    if (user.nombre.lower() in nombre.lower() or 
                        nombre.lower() in user.nombre.lower()):
                        user_id = user.id
                        break
            
            if user_id:
                ticket.asignado_a = user_id
                actualizados += 1
                print(f"   ✅ {ticket.numero}: {nombre} → ID {user_id}")
            else:
                no_mapeados += 1
                print(f"   ⚠️  {ticket.numero}: Sin mapeo para '{nombre}'")
        
        # 5. Guardar
        if actualizados > 0:
            print(f"\n💾 Guardando {actualizados} cambios...")
            try:
                db.session.commit()
                print("✅ Cambios guardados\n")
            except Exception as e:
                print(f"❌ ERROR: {e}\n")
                db.session.rollback()
                return False
        
        # Resumen
        print("=" * 70)
        print(f"  RESUMEN: {actualizados} actualizados | {no_mapeados} sin mapeo")
        print("=" * 70 + "\n")
        
        # Verificación
        pendientes = Ticket.query.filter(
            Ticket.repartidor_nombre.isnot(None),
            Ticket.asignado_a.is_(None)
        ).count()
        
        if pendientes == 0:
            print("✅ ÉXITO: Todos los tickets asignados correctamente\n")
        else:
            print(f"⚠️  ADVERTENCIA: {pendientes} tickets aún sin asignar\n")
        
        return True


if __name__ == '__main__':
    print("\n🚀 Ejecutando migración automática...\n")
    exito = migrar_tickets_render()
    sys.exit(0 if exito else 1)
