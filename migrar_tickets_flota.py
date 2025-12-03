"""
Script de migración para asignar correctamente los tickets a repartidores.

Este script corrige tickets que tienen repartidor_nombre pero asignado_a = NULL,
lo cual impide que los repartidores vean sus tickets asignados.

Uso:
    python migrar_tickets_flota.py
"""

import sys
import os

# Agregar el directorio de belgrano_tickets al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'belgrano_tickets'))

from models import db, Ticket, User
from app import app

def migrar_tickets():
    """
    Migra tickets existentes que tienen repartidor_nombre pero asignado_a NULL.
    """
    with app.app_context():
        print("=" * 60)
        print("MIGRACIÓN DE TICKETS - ASIGNACIÓN A REPARTIDORES")
        print("=" * 60)
        print()
        
        # 1. Obtener todos los usuarios de flota activos
        print("📋 Paso 1: Obteniendo usuarios de flota...")
        usuarios_flota = User.query.filter_by(role='flota', activo=True).all()
        
        if not usuarios_flota:
            print("❌ ERROR: No se encontraron usuarios de flota activos")
            print("   Por favor, crea usuarios de flota antes de ejecutar esta migración")
            return False
        
        print(f"✅ Encontrados {len(usuarios_flota)} usuarios de flota activos:")
        for user in usuarios_flota:
            print(f"   - {user.nombre} (ID: {user.id}, Email: {user.email})")
        print()
        
        # 2. Crear mapeo de nombres a IDs
        print("📋 Paso 2: Creando mapeo nombre → ID...")
        nombre_a_id = {}
        for user in usuarios_flota:
            # Mapear tanto el nombre completo como posibles variaciones
            nombre_a_id[user.nombre] = user.id
            nombre_a_id[user.nombre.lower()] = user.id
            nombre_a_id[user.username] = user.id
            nombre_a_id[user.username.lower()] = user.id
        
        print(f"✅ Mapeo creado con {len(nombre_a_id)} entradas")
        print()
        
        # 3. Encontrar tickets sin asignación correcta
        print("📋 Paso 3: Buscando tickets sin asignación correcta...")
        tickets_sin_asignar = Ticket.query.filter(
            Ticket.repartidor_nombre.isnot(None),
            Ticket.asignado_a.is_(None)
        ).all()
        
        print(f"✅ Encontrados {len(tickets_sin_asignar)} tickets para migrar")
        
        if len(tickets_sin_asignar) == 0:
            print("   No hay tickets que necesiten migración")
            print()
            print("=" * 60)
            print("MIGRACIÓN COMPLETADA - SIN CAMBIOS NECESARIOS")
            print("=" * 60)
            return True
        
        print()
        
        # 4. Actualizar tickets
        print("📋 Paso 4: Actualizando tickets...")
        tickets_actualizados = 0
        tickets_no_mapeados = 0
        
        for ticket in tickets_sin_asignar:
            nombre_repartidor = ticket.repartidor_nombre
            
            # Buscar ID del repartidor
            user_id = None
            
            # Intentar mapeo directo
            if nombre_repartidor in nombre_a_id:
                user_id = nombre_a_id[nombre_repartidor]
            # Intentar mapeo en minúsculas
            elif nombre_repartidor.lower() in nombre_a_id:
                user_id = nombre_a_id[nombre_repartidor.lower()]
            # Buscar por nombre similar
            else:
                for user in usuarios_flota:
                    if (user.nombre.lower() in nombre_repartidor.lower() or 
                        nombre_repartidor.lower() in user.nombre.lower()):
                        user_id = user.id
                        break
            
            if user_id:
                ticket.asignado_a = user_id
                tickets_actualizados += 1
                print(f"   ✅ Ticket #{ticket.numero}: '{nombre_repartidor}' → ID {user_id}")
            else:
                tickets_no_mapeados += 1
                print(f"   ⚠️ Ticket #{ticket.numero}: No se encontró usuario para '{nombre_repartidor}'")
        
        print()
        
        # 5. Guardar cambios
        if tickets_actualizados > 0:
            print("📋 Paso 5: Guardando cambios en la base de datos...")
            try:
                db.session.commit()
                print(f"✅ Cambios guardados exitosamente")
            except Exception as e:
                print(f"❌ ERROR guardando cambios: {e}")
                db.session.rollback()
                return False
        else:
            print("📋 Paso 5: No hay cambios para guardar")
        
        print()
        print("=" * 60)
        print("RESUMEN DE LA MIGRACIÓN")
        print("=" * 60)
        print(f"Total de tickets procesados:     {len(tickets_sin_asignar)}")
        print(f"Tickets actualizados:            {tickets_actualizados}")
        print(f"Tickets sin mapeo:               {tickets_no_mapeados}")
        print("=" * 60)
        
        return True


def verificar_migracion():
    """
    Verifica que la migración se haya ejecutado correctamente.
    """
    with app.app_context():
        print()
        print("=" * 60)
        print("VERIFICACIÓN DE LA MIGRACIÓN")
        print("=" * 60)
        print()
        
        # Verificar tickets pendientes
        tickets_pendientes = Ticket.query.filter(
            Ticket.repartidor_nombre.isnot(None),
            Ticket.asignado_a.is_(None)
        ).count()
        
        print(f"Tickets con repartidor pero sin asignado_a: {tickets_pendientes}")
        
        if tickets_pendientes == 0:
            print("✅ MIGRACIÓN EXITOSA - Todos los tickets están asignados correctamente")
        else:
            print(f"⚠️ ADVERTENCIA - Aún quedan {tickets_pendientes} tickets sin asignar")
        
        print()
        
        # Mostrar distribución de tickets por repartidor
        print("Distribución de tickets por repartidor:")
        usuarios_flota = User.query.filter_by(role='flota', activo=True).all()
        
        for user in usuarios_flota:
            count = Ticket.query.filter_by(asignado_a=user.id).count()
            print(f"   {user.nombre} (ID: {user.id}): {count} tickets")
        
        print()
        print("=" * 60)


if __name__ == '__main__':
    print()
    print("⚠️  IMPORTANTE: Esta migración actualizará la base de datos")
    print("   Asegúrate de tener un backup antes de continuar")
    print()
    
    respuesta = input("¿Deseas continuar con la migración? (si/no): ").lower().strip()
    
    if respuesta in ['si', 's', 'yes', 'y']:
        print()
        exito = migrar_tickets()
        
        if exito:
            verificar_migracion()
            print()
            print("✅ Proceso completado con éxito")
            print()
        else:
            print()
            print("❌ El proceso falló - revisa los errores arriba")
            print()
            sys.exit(1)
    else:
        print()
        print("❌ Migración cancelada por el usuario")
        print()
        sys.exit(0)
