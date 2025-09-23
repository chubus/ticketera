#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Sincronización DevOps con Belgrano Ahorro
Sincroniza datos entre DevOps y la aplicación principal
"""

import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SincronizadorBelgranoAhorro:
    """Clase para sincronizar datos entre DevOps y Belgrano Ahorro"""
    
    def __init__(self, db_path: str = None):
        """Inicializar sincronizador"""
        if db_path is None:
            # Buscar la base de datos de Belgrano Ahorro
            possible_paths = [
                'belgrano_ahorro.db',
                '../belgrano_ahorro.db',
                '../../belgrano_ahorro.db',
                os.path.join(os.path.dirname(__file__), 'belgrano_ahorro.db'),
                os.path.join(os.path.dirname(__file__), '..', 'belgrano_ahorro.db')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    db_path = path
                    break
            
            if not db_path:
                raise FileNotFoundError("No se encontró la base de datos belgrano_ahorro.db")
        
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        """Inicializar tablas necesarias en Belgrano Ahorro"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Crear tabla de negocios si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS negocios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        descripcion TEXT,
                        direccion TEXT,
                        telefono TEXT,
                        email TEXT,
                        activo BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Crear tabla de productos si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS productos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        descripcion TEXT,
                        precio REAL NOT NULL,
                        categoria TEXT,
                        stock INTEGER DEFAULT 0,
                        stock_minimo INTEGER DEFAULT 0,
                        negocio_id INTEGER,
                        activo BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (negocio_id) REFERENCES negocios(id)
                    )
                ''')
                
                # Crear tabla de ofertas si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ofertas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        titulo TEXT NOT NULL,
                        descripcion TEXT,
                        productos TEXT,  -- JSON string de productos
                        hasta_agotar_stock BOOLEAN DEFAULT 0,
                        activa BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Crear tabla de categorías si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categorias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL UNIQUE,
                        descripcion TEXT,
                        activa BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Tablas de Belgrano Ahorro inicializadas correctamente")
                
        except Exception as e:
            logger.error(f"Error inicializando tablas: {e}")
            raise
    
    def sincronizar_negocios(self):
        """Sincronizar negocios desde DevOps a Belgrano Ahorro"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener negocios existentes
                cursor.execute('SELECT * FROM negocios ORDER BY fecha_creacion DESC')
                rows = cursor.fetchall()
                
                negocios = []
                for row in rows:
                    negocios.append({
                        'id': row[0],
                        'nombre': row[1],
                        'descripcion': row[2],
                        'direccion': row[3],
                        'telefono': row[4],
                        'email': row[5],
                        'activo': bool(row[6]),
                        'fecha_creacion': row[7],
                        'fecha_actualizacion': row[8]
                    })
                
                logger.info(f"Sincronización de negocios completada: {len(negocios)} negocios")
                return negocios
                
        except Exception as e:
            logger.error(f"Error sincronizando negocios: {e}")
            return []
    
    def sincronizar_productos(self):
        """Sincronizar productos desde DevOps a Belgrano Ahorro"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener productos existentes
                cursor.execute('SELECT * FROM productos ORDER BY fecha_creacion DESC')
                rows = cursor.fetchall()
                
                productos = []
                for row in rows:
                    productos.append({
                        'id': row[0],
                        'nombre': row[1],
                        'descripcion': row[2],
                        'precio': row[3],
                        'categoria': row[4],
                        'stock': row[5],
                        'stock_minimo': row[6],
                        'negocio_id': row[7],
                        'activo': bool(row[8]),
                        'fecha_creacion': row[9],
                        'fecha_actualizacion': row[10]
                    })
                
                logger.info(f"Sincronización de productos completada: {len(productos)} productos")
                return productos
                
        except Exception as e:
            logger.error(f"Error sincronizando productos: {e}")
            return []
    
    def sincronizar_ofertas(self):
        """Sincronizar ofertas desde DevOps a Belgrano Ahorro"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener ofertas existentes
                cursor.execute('SELECT * FROM ofertas ORDER BY fecha_creacion DESC')
                rows = cursor.fetchall()
                
                ofertas = []
                for row in rows:
                    ofertas.append({
                        'id': row[0],
                        'titulo': row[1],
                        'descripcion': row[2],
                        'productos': json.loads(row[3]) if row[3] else [],
                        'hasta_agotar_stock': bool(row[4]),
                        'activa': bool(row[5]),
                        'fecha_creacion': row[6],
                        'fecha_actualizacion': row[7]
                    })
                
                logger.info(f"Sincronización de ofertas completada: {len(ofertas)} ofertas")
                return ofertas
                
        except Exception as e:
            logger.error(f"Error sincronizando ofertas: {e}")
            return []
    
    def sincronizar_todo(self):
        """Sincronizar todos los datos"""
        try:
            logger.info("Iniciando sincronización completa con Belgrano Ahorro...")
            
            negocios = self.sincronizar_negocios()
            productos = self.sincronizar_productos()
            ofertas = self.sincronizar_ofertas()
            
            resultado = {
                'negocios': len(negocios),
                'productos': len(productos),
                'ofertas': len(ofertas),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            logger.info(f"Sincronización completa: {resultado}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error en sincronización completa: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Función principal para ejecutar sincronización"""
    try:
        sincronizador = SincronizadorBelgranoAhorro()
        resultado = sincronizador.sincronizar_todo()
        
        print("=== SINCRONIZACIÓN DEVOPS CON BELGRANO AHORRO ===")
        print(f"Negocios sincronizados: {resultado.get('negocios', 0)}")
        print(f"Productos sincronizados: {resultado.get('productos', 0)}")
        print(f"Ofertas sincronizadas: {resultado.get('ofertas', 0)}")
        print(f"Timestamp: {resultado.get('timestamp', 'N/A')}")
        print(f"Status: {resultado.get('status', 'unknown')}")
        
        if resultado.get('status') == 'success':
            print("✅ Sincronización completada exitosamente")
        else:
            print("❌ Error en sincronización")
            
    except Exception as e:
        print(f"❌ Error ejecutando sincronización: {e}")

if __name__ == "__main__":
    main()
