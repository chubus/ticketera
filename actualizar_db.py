#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar la base de datos de la Ticketera
Agrega el campo 'total' al modelo Ticket
"""

import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar los módulos
sys.path.append(str(Path(__file__).parent))

from app import app, db
from models import Ticket

def actualizar_base_datos():
    """Actualizar la base de datos para agregar el campo total"""
    with app.app_context():
        try:
            print("🔧 Actualizando base de datos...")
            
            # Verificar si la columna total existe
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('ticket')]
            
            if 'total' not in columns:
                print("📝 Agregando columna 'total' a la tabla ticket...")
                
                # Agregar la columna total
                db.engine.execute('ALTER TABLE ticket ADD COLUMN total FLOAT DEFAULT 0.0')
                
                print("✅ Columna 'total' agregada exitosamente")
            else:
                print("✅ La columna 'total' ya existe")
            
            # Verificar que la tabla se actualizó correctamente
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('ticket')]
            print(f"📊 Columnas en tabla ticket: {columns}")
            
            # Contar tickets existentes
            total_tickets = Ticket.query.count()
            print(f"📊 Total de tickets en BD: {total_tickets}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error actualizando base de datos: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    success = actualizar_base_datos()
    if success:
        print("🎉 Base de datos actualizada exitosamente")
        sys.exit(0)
    else:
        print("💥 Error actualizando base de datos")
        sys.exit(1)
