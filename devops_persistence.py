#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Persistencia DevOps
Conecta DevOps con la base de datos de Belgrano Ahorro
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DevOpsPersistence:
    """Clase para manejar la persistencia de datos DevOps"""
    
    def __init__(self, db_path: str = None):
        """Inicializar conexión a base de datos"""
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
        self.init_database()
    
    def init_database(self):
        """Inicializar tablas necesarias para DevOps"""
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
                        image_url TEXT,
                        FOREIGN KEY (negocio_id) REFERENCES negocios(id)
                    )
                ''')
                
                # Crear tabla de sucursales si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sucursales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        direccion TEXT,
                        telefono TEXT,
                        email TEXT,
                        negocio_id INTEGER NOT NULL,
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
                
                # Crear historial de precios si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS precios_historial (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        precio_anterior REAL NOT NULL,
                        precio_nuevo REAL NOT NULL,
                        motivo TEXT,
                        fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
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
                logger.info("Base de datos DevOps inicializada correctamente")
                
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    def crear_negocio(self, datos: Dict) -> Dict:
        """Crear un nuevo negocio"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO negocios (nombre, descripcion, direccion, telefono, email, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datos['nombre'],
                    datos.get('descripcion', ''),
                    datos.get('direccion', ''),
                    datos.get('telefono', ''),
                    datos.get('email', ''),
                    datos.get('activo', True)
                ))
                
                negocio_id = cursor.lastrowid
                conn.commit()
                
                # Obtener el negocio creado
                cursor.execute('SELECT * FROM negocios WHERE id = ?', (negocio_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'nombre': row[1],
                        'descripcion': row[2],
                        'direccion': row[3],
                        'telefono': row[4],
                        'email': row[5],
                        'activo': bool(row[6]),
                        'fecha_creacion': row[7],
                        'fecha_actualizacion': row[8]
                    }
                
        except Exception as e:
            logger.error(f"Error creando negocio: {e}")
            raise
    
    def obtener_negocios(self) -> List[Dict]:
        """Obtener todos los negocios"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                
                return negocios
                
        except Exception as e:
            logger.error(f"Error obteniendo negocios: {e}")
            return []
    
    def crear_producto(self, datos: Dict) -> Dict:
        """Crear un nuevo producto"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO productos (nombre, descripcion, precio, categoria, stock, stock_minimo, negocio_id, activo, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datos['nombre'],
                    datos.get('descripcion', ''),
                    datos['precio'],
                    datos.get('categoria', 'General'),
                    datos.get('stock', 0),
                    datos.get('stock_minimo', 0),
                    datos.get('negocio_id'),
                    datos.get('activo', True),
                    datos.get('image_url', '')
                ))
                
                producto_id = cursor.lastrowid
                conn.commit()
                
                # Obtener el producto creado
                cursor.execute('SELECT * FROM productos WHERE id = ?', (producto_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
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
                        'activo': bool(row[8]),
                        'fecha_creacion': row[9],
                        'fecha_actualizacion': row[10],
                        'image_url': row[11] if len(row) > 11 else ''
                    }
                
        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            raise
    
    def obtener_productos(self) -> List[Dict]:
        """Obtener todos los productos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                        'activo': bool(row[8]),
                        'fecha_creacion': row[9],
                        'fecha_actualizacion': row[10],
                        'image_url': row[11] if len(row) > 11 else ''
                    })
                
                return productos
                
        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}")
            return []

    def obtener_categorias(self) -> List[Dict]:
        """Obtener todas las categorías"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nombre, descripcion, activa, fecha_creacion FROM categorias ORDER BY nombre ASC')
                rows = cursor.fetchall()
                categorias: List[Dict] = []
                for row in rows:
                    categorias.append({
                        'id': row[0],
                        'nombre': row[1],
                        'descripcion': row[2],
                        'activa': bool(row[3]),
                        'fecha_creacion': row[4]
                    })
                return categorias
        except Exception as e:
            logger.error(f"Error obteniendo categorías: {e}")
            return []

    def actualizar_precio_producto(self, producto_id: int, nuevo_precio: float, motivo: str = '') -> Dict:
        """Actualizar el precio de un producto y registrar el historial"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Obtener precio anterior
                cursor.execute('SELECT precio FROM productos WHERE id = ?', (int(producto_id),))
                row = cursor.fetchone()
                if not row:
                    raise ValueError('Producto no encontrado')
                precio_anterior = float(row[0])

                # Actualizar precio
                cursor.execute('UPDATE productos SET precio = ?, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?', (float(nuevo_precio), int(producto_id)))

                # Registrar historial
                cursor.execute('INSERT INTO precios_historial (producto_id, precio_anterior, precio_nuevo, motivo) VALUES (?, ?, ?, ?)', (int(producto_id), precio_anterior, float(nuevo_precio), motivo or 'Actualización desde DevOps'))

                conn.commit()

                # Devolver producto actualizado
                cursor.execute('SELECT * FROM productos WHERE id = ?', (int(producto_id),))
                p = cursor.fetchone()
                return {
                    'id': p[0], 'nombre': p[1], 'descripcion': p[2], 'precio': p[3], 'categoria': p[4],
                    'stock': p[5], 'stock_minimo': p[6], 'negocio_id': p[7], 'activo': bool(p[8]),
                    'fecha_creacion': p[9], 'fecha_actualizacion': p[10]
                }
        except Exception as e:
            logger.error(f"Error actualizando precio: {e}")
            raise

    def obtener_precios(self) -> List[Dict]:
        """Obtener lista de productos con sus precios y último cambio"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.nombre, p.precio, p.categoria,
                           (SELECT ph.precio_nuevo FROM precios_historial ph WHERE ph.producto_id = p.id ORDER BY ph.fecha_cambio DESC LIMIT 1) AS ultimo_precio,
                           (SELECT ph.fecha_cambio FROM precios_historial ph WHERE ph.producto_id = p.id ORDER BY ph.fecha_cambio DESC LIMIT 1) AS fecha_ultimo
                    FROM productos p
                    ORDER BY p.fecha_actualizacion DESC
                ''')
                rows = cursor.fetchall()
                precios = []
                for r in rows:
                    precios.append({
                        'producto_id': r[0],
                        'nombre': r[1],
                        'precio': r[2],
                        'categoria': r[3],
                        'ultimo_precio': r[4] if r[4] is not None else r[2],
                        'fecha_ultimo': r[5]
                    })
                return precios
        except Exception as e:
            logger.error(f"Error obteniendo precios: {e}")
            return []
    
    def crear_oferta(self, datos: Dict) -> Dict:
        """Crear una nueva oferta"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convertir lista de productos a JSON string
                productos_json = json.dumps(datos.get('productos', []))
                
                cursor.execute('''
                    INSERT INTO ofertas (titulo, descripcion, productos, hasta_agotar_stock, activa)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    datos['titulo'],
                    datos.get('descripcion', ''),
                    productos_json,
                    datos.get('hasta_agotar_stock', False),
                    datos.get('activa', True)
                ))
                
                oferta_id = cursor.lastrowid
                conn.commit()
                
                # Obtener la oferta creada
                cursor.execute('SELECT * FROM ofertas WHERE id = ?', (oferta_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'titulo': row[1],
                        'descripcion': row[2],
                        'productos': json.loads(row[3]) if row[3] else [],
                        'hasta_agotar_stock': bool(row[4]),
                        'activa': bool(row[5]),
                        'fecha_creacion': row[6],
                        'fecha_actualizacion': row[7]
                    }
                
        except Exception as e:
            logger.error(f"Error creando oferta: {e}")
            raise
    
    def obtener_ofertas(self) -> List[Dict]:
        """Obtener todas las ofertas"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                
                return ofertas
                
        except Exception as e:
            logger.error(f"Error obteniendo ofertas: {e}")
            return []
    
    def crear_sucursal(self, datos: Dict) -> Dict:
        """Crear una nueva sucursal asociada a un negocio"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sucursales (nombre, direccion, telefono, email, negocio_id, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datos['nombre'],
                    datos.get('direccion', ''),
                    datos.get('telefono', ''),
                    datos.get('email', ''),
                    int(datos['negocio_id']),
                    datos.get('activo', True)
                ))
                sucursal_id = cursor.lastrowid
                conn.commit()

                cursor.execute('SELECT * FROM sucursales WHERE id = ?', (sucursal_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'nombre': row[1],
                        'direccion': row[2],
                        'telefono': row[3],
                        'email': row[4],
                        'negocio_id': row[5],
                        'activo': bool(row[6]),
                        'fecha_creacion': row[7],
                        'fecha_actualizacion': row[8]
                    }
        except Exception as e:
            logger.error(f"Error creando sucursal: {e}")
            raise

    def obtener_sucursales(self, negocio_id: Optional[int] = None) -> List[Dict]:
        """Obtener sucursales, opcionalmente filtradas por negocio"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if negocio_id is not None:
                    cursor.execute('SELECT * FROM sucursales WHERE negocio_id = ? ORDER BY fecha_creacion DESC', (int(negocio_id),))
                else:
                    cursor.execute('SELECT * FROM sucursales ORDER BY fecha_creacion DESC')
                rows = cursor.fetchall()
                sucursales = []
                for row in rows:
                    sucursales.append({
                        'id': row[0],
                        'nombre': row[1],
                        'direccion': row[2],
                        'telefono': row[3],
                        'email': row[4],
                        'negocio_id': row[5],
                        'activo': bool(row[6]),
                        'fecha_creacion': row[7],
                        'fecha_actualizacion': row[8]
                    })
                return sucursales
        except Exception as e:
            logger.error(f"Error obteniendo sucursales: {e}")
            return []

    def sincronizar_con_belgrano_ahorro(self):
        """Sincronizar datos con la aplicación principal de Belgrano Ahorro"""
        try:
            # Aquí se implementaría la lógica de sincronización
            # Por ahora, los datos ya están en la misma base de datos
            logger.info("Sincronización con Belgrano Ahorro completada")
            return True
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            return False

# Instancia global para uso en DevOps
_devops_db = None

def get_devops_db():
    """Obtener instancia global de la base de datos DevOps"""
    global _devops_db
    if _devops_db is None:
        _devops_db = DevOpsPersistence()
    return _devops_db
