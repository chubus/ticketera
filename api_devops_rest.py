#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIs REST para DevOps
Rutas /api/devops/* para integración con Belgrano Ahorro
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Crear blueprint para APIs REST
api_devops_bp = Blueprint('api_devops', __name__, url_prefix='/api/devops')

def require_devops_auth():
    """Verificar autenticación DevOps"""
    if not session.get('devops_authenticated'):
        return jsonify({'error': 'No autorizado', 'code': 401}), 401
    return None

@api_devops_bp.route('/negocios', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_negocios():
    """API REST para gestión de negocios"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar negocios
            negocios = db.obtener_negocios()
            return jsonify({
                'status': 'success',
                'data': negocios,
                'total': len(negocios),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear negocio
            data = request.get_json() or {}
            required_fields = ['nombre']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} es requerido'}), 400
            
            nuevo_negocio = db.crear_negocio({
                'nombre': data['nombre'],
                'descripcion': data.get('descripcion', ''),
                'direccion': data.get('direccion', ''),
                'telefono': data.get('telefono', ''),
                'email': data.get('email', ''),
                'activo': data.get('activo', True)
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Negocio creado exitosamente',
                'data': nuevo_negocio
            }), 201
        
        elif request.method == 'PUT':
            # Actualizar negocio (implementar si necesario)
            return jsonify({'error': 'PUT no implementado aún'}), 501
        
        elif request.method == 'DELETE':
            # Eliminar negocio (implementar si necesario)
            return jsonify({'error': 'DELETE no implementado aún'}), 501
            
    except Exception as e:
        logger.error(f"Error en API negocios: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/productos', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_productos():
    """API REST para gestión de productos"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar productos
            productos = db.obtener_productos()
            return jsonify({
                'status': 'success',
                'data': productos,
                'total': len(productos),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear producto
            data = request.get_json() or {}
            required_fields = ['nombre', 'precio']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} es requerido'}), 400
            
            nuevo_producto = db.crear_producto({
                'nombre': data['nombre'],
                'descripcion': data.get('descripcion', ''),
                'precio': float(data['precio']),
                'categoria': data.get('categoria', 'General'),
                'stock': data.get('stock', 0),
                'negocio_id': data.get('negocio_id'),
                'activo': data.get('activo', True)
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Producto creado exitosamente',
                'data': nuevo_producto
            }), 201
        
        elif request.method == 'PUT':
            # Actualizar producto (implementar si necesario)
            return jsonify({'error': 'PUT no implementado aún'}), 501
        
        elif request.method == 'DELETE':
            # Eliminar producto (implementar si necesario)
            return jsonify({'error': 'DELETE no implementado aún'}), 501
            
    except Exception as e:
        logger.error(f"Error en API productos: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/ofertas', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_ofertas():
    """API REST para gestión de ofertas"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar ofertas
            ofertas = db.obtener_ofertas()
            return jsonify({
                'status': 'success',
                'data': ofertas,
                'total': len(ofertas),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear oferta
            data = request.get_json() or {}
            required_fields = ['titulo']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} es requerido'}), 400
            
            nueva_oferta = db.crear_oferta({
                'titulo': data['titulo'],
                'descripcion': data.get('descripcion', ''),
                'productos': data.get('productos', []),
                'hasta_agotar_stock': data.get('hasta_agotar_stock', False),
                'activa': data.get('activa', True)
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Oferta creada exitosamente',
                'data': nueva_oferta
            }), 201
        
        elif request.method == 'PUT':
            # Actualizar oferta (implementar si necesario)
            return jsonify({'error': 'PUT no implementado aún'}), 501
        
        elif request.method == 'DELETE':
            # Eliminar oferta (implementar si necesario)
            return jsonify({'error': 'DELETE no implementado aún'}), 501
            
    except Exception as e:
        logger.error(f"Error en API ofertas: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/precios', methods=['GET', 'POST', 'PUT'])
def api_precios():
    """API REST para gestión de precios"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar precios
            precios = db.obtener_precios()
            return jsonify({
                'status': 'success',
                'data': precios,
                'total': len(precios),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear/actualizar precio
            data = request.get_json() or {}
            required_fields = ['producto_id', 'nuevo_precio']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} es requerido'}), 400
            
            producto_actualizado = db.actualizar_precio_producto(
                int(data['producto_id']),
                float(data['nuevo_precio']),
                data.get('motivo', 'Actualización desde API')
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Precio actualizado exitosamente',
                'data': producto_actualizado
            }), 201
        
        elif request.method == 'PUT':
            # Actualizar precio (alias de POST)
            return api_precios()
            
    except Exception as e:
        logger.error(f"Error en API precios: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/sucursales', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_sucursales():
    """API REST para gestión de sucursales"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar sucursales
            negocio_id = request.args.get('negocio_id')
            sucursales = db.obtener_sucursales(int(negocio_id) if negocio_id else None)
            return jsonify({
                'status': 'success',
                'data': sucursales,
                'total': len(sucursales),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear sucursal
            data = request.get_json() or {}
            required_fields = ['nombre', 'negocio_id']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} es requerido'}), 400
            
            nueva_sucursal = db.crear_sucursal({
                'nombre': data['nombre'],
                'direccion': data.get('direccion', ''),
                'telefono': data.get('telefono', ''),
                'email': data.get('email', ''),
                'negocio_id': int(data['negocio_id']),
                'activo': data.get('activo', True)
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Sucursal creada exitosamente',
                'data': nueva_sucursal
            }), 201
        
        elif request.method == 'PUT':
            # Actualizar sucursal (implementar si necesario)
            return jsonify({'error': 'PUT no implementado aún'}), 501
        
        elif request.method == 'DELETE':
            # Eliminar sucursal (implementar si necesario)
            return jsonify({'error': 'DELETE no implementado aún'}), 501
            
    except Exception as e:
        logger.error(f"Error en API sucursales: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/categorias', methods=['GET', 'POST'])
def api_categorias():
    """API REST para gestión de categorías"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from devops_persistence import get_devops_db
        db = get_devops_db()
        
        if request.method == 'GET':
            # Listar categorías
            categorias = db.obtener_categorias()
            return jsonify({
                'status': 'success',
                'data': categorias,
                'total': len(categorias),
                'timestamp': datetime.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Crear categoría
            data = request.get_json() or {}
            if not data.get('nombre'):
                return jsonify({'error': 'nombre es requerido'}), 400
            
            # Implementar crear_categoria si no existe
            return jsonify({'error': 'Crear categoría no implementado aún'}), 501
            
    except Exception as e:
        logger.error(f"Error en API categorías: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/sync', methods=['POST'])
def api_sync():
    """API REST para sincronización con Belgrano Ahorro"""
    auth_error = require_devops_auth()
    if auth_error:
        return auth_error
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from sincronizar_belgrano_ahorro import SincronizadorBelgranoAhorro
        
        sincronizador = SincronizadorBelgranoAhorro()
        resultado = sincronizador.sincronizar_todo()
        
        return jsonify({
            'status': 'success',
            'message': 'Sincronización completada',
            'data': resultado,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return jsonify({'error': str(e)}), 500

@api_devops_bp.route('/health', methods=['GET'])
def api_health():
    """API REST para verificar estado del sistema"""
    return jsonify({
        'status': 'success',
        'message': 'DevOps API funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            '/api/devops/negocios',
            '/api/devops/productos', 
            '/api/devops/ofertas',
            '/api/devops/precios',
            '/api/devops/sucursales',
            '/api/devops/categorias',
            '/api/devops/sync',
            '/api/devops/health'
        ]
    })
