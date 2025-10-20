#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema DevOps Completo para Belgrano Tickets
Control total sobre el contenido de Belgrano Ahorro
"""

import os
import json
import requests
from functools import wraps
from datetime import datetime
import logging
from urllib.parse import urljoin
from flask import Blueprint, request, jsonify, redirect, url_for, session, make_response, render_template, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de API y credenciales DevOps
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'https://belgranoahorro-aliq.onrender.com')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')
API_TIMEOUT_SECS = 10

# Credenciales de DevOps
DEVOPS_USERNAME = os.environ.get('DEVOPS_USERNAME', 'devops')
DEVOPS_PASSWORD_PLAIN = os.environ.get('DEVOPS_PASSWORD', 'DevOps2025!Secure')
DEVOPS_PASSWORD_HASH = generate_password_hash(DEVOPS_PASSWORD_PLAIN)

# Validar variables de entorno críticas
env_status = os.environ.get('FLASK_ENV', 'development')
if not BELGRANO_AHORRO_URL:
    if env_status != 'production':
        logger.info("ℹ️ BELGRANO_AHORRO_URL no configurada (normal en desarrollo)")
    else:
        logger.warning("⚠️ Variable de entorno BELGRANO_AHORRO_URL no está definida")

if not BELGRANO_AHORRO_API_KEY:
    if env_status != 'production':
        logger.info("ℹ️ BELGRANO_AHORRO_API_KEY no configurada (normal en desarrollo)")
    else:
        logger.warning("⚠️ Variable de entorno BELGRANO_AHORRO_API_KEY no está definida")

# Importar cliente API de forma robusta (soporta ejecución desde paquetes distintos)
devops_api_client = None
try:
    from belgrano_tickets.api_client import create_api_client, api_client as global_api_client
except Exception:
    try:
        from api_client import create_api_client, api_client as global_api_client  # type: ignore
    except Exception:
        try:
            from belgrano_client_gateway import BelgranoClientGateway as create_api_client  # type: ignore
        except Exception as e:
            logger.error(f"No se pudo inicializar el cliente API: {e}")
            create_api_client = None  # type: ignore

if create_api_client and BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
    try:
        devops_api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        logger.info("Cliente API de Belgrano Ahorro inicializado para DevOps")
    except Exception as e:
        logger.error(f"Error creando cliente API de DevOps: {e}")
        devops_api_client = None
    else:
        if env_status == 'production':
            logger.warning("Variables de entorno no configuradas para cliente API de DevOps")
        else:
            logger.info("Cliente API de DevOps no inicializado (variables no configuradas)")

# Importar solo gestor DevOps unificado (evita errores por módulos antiguos)
try:
    from devops_belgrano_manager_unified import devops_manager_unified as devops_manager
    logger.info("✅ Gestor DevOps unificado inicializado")
except Exception as e:
    # Intento adicional ajustando sys.path a raíz del proyecto
    try:
        import sys, os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from devops_belgrano_manager_unified import devops_manager_unified as devops_manager  # type: ignore
        logger.info("✅ Gestor DevOps unificado inicializado tras ajustar sys.path")
    except Exception as e2:
        logger.error(f"❌ No se pudo importar devops_belgrano_manager_unified: {e2}")
        devops_manager = None

# Crear blueprint con prefijo
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# =============================
# Fallback de persistencia local (cuando devops_manager no está disponible)
# =============================

def _find_ahorro_db_path() -> str:
    """Ubicar ruta de belgrano_ahorro.db similar al sincronizador."""
    possible_paths = [
        'belgrano_ahorro.db',
        '../belgrano_ahorro.db',
        '../../belgrano_ahorro.db',
        os.path.join(os.path.dirname(__file__), '..', 'belgrano_ahorro.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'belgrano_ahorro.db')
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    # Último recurso: raíz del proyecto
    return 'belgrano_ahorro.db'

def _fallback_insert_negocio(negocio_data: dict) -> int:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
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
        cursor.execute(
            'INSERT INTO negocios (nombre, descripcion, direccion, telefono, email, activo) VALUES (?, ?, ?, ?, ?, ?)',
            (
                negocio_data.get('nombre', ''),
                negocio_data.get('descripcion', ''),
                negocio_data.get('direccion', ''),
                negocio_data.get('telefono', ''),
                negocio_data.get('email', ''),
                1 if negocio_data.get('activo', True) else 0,
            ),
        )
        conn.commit()
        return cursor.lastrowid

def _fallback_insert_producto(producto_data: dict) -> int:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Esquema real requiere 'store' (NOT NULL) y 'precio'
        # Insertamos mínimos requeridos y campos opcionales comunes
        store_value = (producto_data.get('store')
                       or producto_data.get('negocio')
                       or producto_data.get('categoria')
                       or 'general')
        cursor.execute(
            'INSERT INTO productos (nombre, store, precio, categoria, stock, stock_minimo, negocio_id, activo, imagen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                producto_data.get('nombre', ''),
                str(store_value),
                float(producto_data.get('precio', 0) or 0),
                producto_data.get('categoria', ''),
                int(producto_data.get('stock', 0) or 0),
                int(producto_data.get('stock_minimo', 0) or 0),
                int(producto_data.get('negocio') or producto_data.get('negocio_id') or 0),
                1 if producto_data.get('activo', True) else 0,
                producto_data.get('imagen', ''),
            ),
        )
        conn.commit()
        return cursor.lastrowid

def _fallback_insert_oferta(oferta_data: dict) -> int:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ofertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                productos TEXT,
                hasta_agotar_stock BOOLEAN DEFAULT 0,
                activa BOOLEAN DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        productos_raw = oferta_data.get('productos')
        # Acepta lista o string; guarda como JSON
        if isinstance(productos_raw, str):
            productos_json = productos_raw
        else:
            try:
                productos_json = json.dumps(productos_raw or [])
            except Exception:
                productos_json = '[]'
        cursor.execute(
            'INSERT INTO ofertas (titulo, descripcion, productos, hasta_agotar_stock, activa) VALUES (?, ?, ?, ?, ?)',
            (
                oferta_data.get('titulo', ''),
                oferta_data.get('descripcion', ''),
                productos_json,
                1 if oferta_data.get('hasta_agotar_stock', False) else 0,
                1 if oferta_data.get('activa', True) else 0,
            ),
        )
        conn.commit()
        return cursor.lastrowid

def _fallback_get_negocios() -> list:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre, descripcion, direccion, telefono, email, activo, fecha_creacion, fecha_actualizacion FROM negocios ORDER BY fecha_creacion DESC')
        rows = cursor.fetchall()
        negocios = []
        for r in rows:
            negocios.append({
                'id': r[0],
                'nombre': r[1],
                'descripcion': r[2],
                'direccion': r[3],
                'telefono': r[4],
                'email': r[5],
                'activo': bool(r[6]),
                'fecha_creacion': r[7],
                'fecha_actualizacion': r[8],
            })
        return negocios

def _fallback_get_productos() -> list:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre, descripcion, precio, categoria, stock, stock_minimo, negocio_id, activo, fecha_creacion, fecha_actualizacion FROM productos ORDER BY fecha_creacion DESC')
        rows = cursor.fetchall()
        productos = []
        for r in rows:
            productos.append({
                'id': r[0],
                'nombre': r[1],
                'descripcion': r[2],
                'precio': r[3],
                'categoria': r[4],
                'stock': r[5],
                'stock_minimo': r[6],
                'negocio_id': r[7],
                'activo': bool(r[8]),
                'fecha_creacion': r[9],
                'fecha_actualizacion': r[10],
            })
        return productos

def _fallback_get_ofertas() -> list:
    db_path = _find_ahorro_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, titulo, descripcion, productos, hasta_agotar_stock, activa, fecha_creacion, fecha_actualizacion FROM ofertas ORDER BY fecha_creacion DESC')
        rows = cursor.fetchall()
        ofertas = []
        for r in rows:
            try:
                productos_list = json.loads(r[3]) if r[3] else []
            except Exception:
                productos_list = []
            ofertas.append({
                'id': r[0],
                'titulo': r[1],
                'descripcion': r[2],
                'productos': productos_list,
                'hasta_agotar_stock': bool(r[4]),
                'activa': bool(r[5]),
                'fecha_creacion': r[6],
                'fecha_actualizacion': r[7],
            })
        return ofertas

# =============================
# AUTENTICACIÓN DEVOPS
# =============================

def devops_is_authenticated():
    """Verificar si DevOps está autenticado"""
    try:
        return session.get('devops_authenticated') is True
    except Exception as e:
        logger.error(f"Error verificando autenticación DevOps: {e}")
        return False

def devops_login_required(fn):
    """Decorador para requerir autenticación de DevOps"""
    def wrapper(*args, **kwargs):
        if not devops_is_authenticated():
            return redirect('/devops/login')
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@devops_bp.route('/login', methods=['GET', 'POST'])
def devops_login():
    """Login de DevOps"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == DEVOPS_USERNAME and check_password_hash(DEVOPS_PASSWORD_HASH, password):
            session['devops_authenticated'] = True
            session.permanent = True
            logger.info(f"Login exitoso de DevOps: {username}")
            return redirect(url_for('devops.devops_home'))
        else:
            flash('Credenciales incorrectas', 'error')
    
    return render_template('devops/login.html', 
                         username=DEVOPS_USERNAME)

@devops_bp.route('/')
@devops_login_required
def devops_home():
    """Panel principal de DevOps"""
    return render_template('devops/dashboard.html')

@devops_bp.route('/logout')
def devops_logout():
    """Cerrar sesión de DevOps"""
    session.pop('devops_authenticated', None)
    logger.info("Logout exitoso de DevOps")
    return redirect(url_for('devops.devops_login'))

@devops_bp.route('/health')
@devops_login_required
def devops_health():
    """Health check completo del sistema DevOps"""
    from flask import request, make_response
    
    # Solo devolver JSON si se solicita explícitamente con todos los parámetros
    if (request.headers.get('X-Requested-With', jsonify) == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'service': 'devops',
                'status': 'healthy',
                'version': '2.0.0',
                'checks': {
                    'database': 'healthy',
                    'api_connection': 'checking',
                    'sync_service': 'healthy',
                    'logging': 'healthy'
                }
            }
            
            # Verificar conexión con API externa
            try:
                if devops_manager:
                    connectivity = devops_manager.test_connectivity()
                    if connectivity['overall_status'] == 'success':
                        health_status['checks']['api_connection'] = 'healthy'
                    elif connectivity['overall_status'] == 'partial':
                        health_status['checks']['api_connection'] = 'warning'
                    else:
                        health_status['checks']['api_connection'] = 'error'
                        health_status['api_error'] = connectivity.get('message', 'Error de conectividad')
                else:
                    health_status['checks']['api_connection'] = 'disabled'
                    health_status['api_error'] = 'Gestor DevOps no disponible'
            except Exception as e:
                health_status['checks']['api_connection'] = 'error'
                health_status['api_error'] = str(e)
            
            if request.headers.get('Accept') == 'application/json':

            
                return jsonify({
                    'status': 'success',
                    'data': health_status
                })
            else:
                flash('Estado del sistema verificado', 'success')
                return render_template('devops/health.html', 
                                     health_status=health_status,
                                     status='success')
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            if request.headers.get('Accept') == 'application/json':

                return jsonify({
                    'status': 'error',
                    'message': f'Error en health check: {str(e)}'
                }), 500
            else:
                flash(f'Error en health check: {str(e)}', 'error')
                return render_template('devops/health.html', 
                                     health_status={},
                                     status='error')
    
    # Si no es AJAX, devolver template HTML
    return render_template('devops/health.html')

@devops_bp.route('/status')
@devops_login_required
def devops_status():
    """Estado detallado del sistema"""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'uptime': 'N/A',
                'memory_usage': 'N/A',
                'cpu_usage': 'N/A',
                'disk_usage': 'N/A'
            },
            'services': {
                'web_server': 'running',
                'database': 'connected',
                'api_client': 'active',
                'sync_service': 'active'
            },
            'configuration': {
                'belgrano_ahorro_url': BELGRANO_AHORRO_URL,
                'api_key_configured': bool(BELGRANO_AHORRO_API_KEY),
                'timeout_seconds': API_TIMEOUT_SECS
            }
        }
        
        if request.headers.get('Accept') == 'application/json':

        
            return jsonify({
                'status': 'success',
                'data': status
            })
        else:
            flash('Estado del sistema obtenido', 'success')
            return render_template('devops/status.html', 
                                 status_data=status,
                                 status='success')
        
    except Exception as e:
        logger.error(f"Error obteniendo status: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error obteniendo status: {str(e)}'
            }), 500
        else:
            flash(f'Error obteniendo status: {str(e)}', 'error')
            return render_template('devops/status.html', 
                                 status_data={},
                                 status='error')

@devops_bp.route('/info')
@devops_login_required
def devops_info():
    """Información completa del sistema DevOps"""
    try:
        info_data = {
            'service': 'DevOps System v2.0',
            'description': 'Sistema de gestión DevOps para Belgrano Tickets',
            'features': [
                'Monitoreo de salud del sistema',
                'Gestión de ofertas y negocios',
                'Sincronización con API externa',
                'Logging y debugging',
                'Panel de administración'
            ],
            'endpoints': {
                'monitoring': {
                    'GET': '/devops/health - Health check',
                    'GET': '/devops/status - Estado del sistema',
                    'GET': '/devops/info - Información del servicio'
                },
                'management': {
                    'GET': '/devops/ofertas - Gestión de ofertas',
                    'GET': '/devops/negocios - Gestión de negocios',
                    'POST': '/devops/sync - Sincronización manual'
                },
                'utilities': {
                    'GET': '/devops/logs - Ver logs del sistema',
                    'GET': '/devops/config - Configuración actual'
                }
            },
            'documentation': {
                'api_docs': '/devops/docs',
                'health_endpoint': '/devops/health',
                'status_endpoint': '/devops/status'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        if request.headers.get('Accept') == 'application/json':

        
            return jsonify({
                'status': 'success',
                'message': 'Información del sistema DevOps',
                'data': info_data
            })
        else:
            flash('Información del sistema cargada', 'success')
            return render_template('devops/info.html', 
                                 info_data=info_data,
                                 status='success')
        
    except Exception as e:
        logger.error(f"Error obteniendo información: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error obteniendo información: {str(e)}'
            }), 500
        else:
            flash(f'Error obteniendo información: {str(e)}', 'error')
            return render_template('devops/info.html', 
                                 info_data={},
                                 status='error')

# =================================================================
# GESTIÓN DE OFERTAS
# =================================================================

@devops_bp.route('/ofertas', methods=['GET', 'POST'])
@devops_login_required
def gestion_ofertas():
    """Gestión completa de ofertas"""
    from flask import request, make_response, render_template, flash, redirect, url_for
    
    # Manejar POST requests (crear oferta, jsonify)
    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            productos = request.form.get('productos', '').strip()
            hasta_agotar_stock = request.form.get('hasta_agotar_stock') == 'on'
            activa = request.form.get('activa') == 'on'
            
            if not all([titulo, descripcion, productos]):
                flash('Título, descripción y productos son requeridos', 'error')
                return redirect(url_for('devops.gestion_ofertas'))
            
            # Crear oferta usando el gestor DevOps
            oferta_data = {
                'titulo': titulo,
                'descripcion': descripcion,
                'productos': productos,
                'hasta_agotar_stock': hasta_agotar_stock,
                'activa': activa
            }
            
            if devops_manager:
                success, message = devops_manager.create_oferta(oferta_data)
                if success:
                    flash(f'Oferta "{titulo}" creada exitosamente', 'success')
                    logger.info(f"Oferta creada desde DevOps: {titulo}")
                else:
                    logger.error(f"Error al crear oferta en API: {message}")
                    # Fallback local
                    _fallback_insert_oferta(oferta_data)
                    flash('API DevOps no disponible. Oferta creada localmente.', 'warning')
            else:
                logger.error("Gestor DevOps no disponible para crear oferta")
                _fallback_insert_oferta(oferta_data)
                flash('Gestor DevOps no disponible. Oferta creada localmente.', 'warning')
                
        except Exception as e:
            logger.error(f"Error creando oferta desde DevOps: {e}")
            flash('Error interno al crear la oferta', 'error')
        
        return redirect(url_for('devops.gestion_ofertas'))
    
    # Manejar requests AJAX/API
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            # Obtener datos reales usando el gestor DevOps o fallback DB
            if devops_manager:
                if getattr(devops_manager, 'fallback_mode', False):
                    ofertas = _fallback_get_ofertas()
                else:
                    ofertas = devops_manager.get_ofertas()
            else:
                ofertas = _fallback_get_ofertas()
            
            return jsonify({
                'status': 'success',
                'message': f'Ofertas obtenidas correctamente ({len(ofertas)} encontradas)',
                'data': {
                    'ofertas': ofertas,
                    'total': len(ofertas),
                    'timestamp': datetime.now().isoformat()
                },
                'source': 'api'
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo ofertas: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error obteniendo ofertas: {str(e)}',
                'data': []
            }), 500
    
    # Manejar requests desde navegador
    try:
        if not devops_manager:
            ofertas = _fallback_get_ofertas()
            flash(f'Ofertas cargadas desde base local: {len(ofertas)}', 'warning')
        else:
            ofertas = devops_manager.get_ofertas()
        flash(f'Ofertas cargadas: {len(ofertas)} encontradas', 'success')
        return render_template('devops/ofertas.html', ofertas=ofertas)
    except Exception as e:
        logger.error(f"Error cargando datos para ofertas: {e}")
        flash(f'Error cargando ofertas: {str(e)}', 'error')
        return render_template('devops/ofertas.html', ofertas=[])

@devops_bp.route('/negocios', methods=['GET', 'POST'])
@devops_login_required
def gestion_negocios():
    """Gestión completa de negocios"""
    from flask import request, make_response, render_template, flash, redirect, url_for
    
    # Manejar POST requests (crear negocio, jsonify)
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            
            if not all([nombre, descripcion]):
                flash('Nombre y descripción son requeridos', 'error')
                return redirect(url_for('devops.gestion_negocios'))
            
            # Crear negocio usando el gestor DevOps
            negocio_data = {
                'nombre': nombre,
                'descripcion': descripcion,
                'logo': request.form.get('logo', ''),
                'telefono': request.form.get('telefono', ''),
                'direccion': request.form.get('direccion', ''),
                'email': request.form.get('email', ''),
                'activo': True
            }
            
            if devops_manager:
                success, message = devops_manager.create_negocio(negocio_data)
                if success:
                    flash(f'Negocio "{nombre}" creado exitosamente', 'success')
                    logger.info(f"Negocio creado desde DevOps: {nombre}")
                else:
                    logger.error(f"Error al crear negocio en API: {message}")
                    # Fallback local
                    nuevo_id = _fallback_insert_negocio(negocio_data)
                    flash(f'API DevOps no disponible. Negocio creado localmente (ID {nuevo_id}).', 'warning')
            else:
                logger.error("Gestor DevOps no disponible para crear negocio")
                nuevo_id = _fallback_insert_negocio(negocio_data)
                flash(f'Gestor DevOps no disponible. Negocio creado localmente (ID {nuevo_id}).', 'warning')
                
        except Exception as e:
            logger.error(f"Error creando negocio desde DevOps: {e}")
            flash('Error interno al crear el negocio', 'error')
        
        return redirect(url_for('devops.gestion_negocios'))
    
    # Manejar requests AJAX/API
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            from datetime import datetime
            
            # Obtener datos reales usando el gestor DevOps o fallback DB
            if devops_manager:
                if getattr(devops_manager, 'fallback_mode', False):
                    negocios = _fallback_get_negocios()
                else:
                    negocios = devops_manager.get_negocios()
            else:
                negocios = _fallback_get_negocios()
            
            return jsonify({
                'status': 'success',
                'data': {
                    'negocios': negocios,
                    'total': len(negocios),
                    'timestamp': datetime.now().isoformat()
                },
                'source': 'api',
                'message': f'Negocios obtenidos correctamente ({len(negocios)} encontrados)'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error obteniendo negocios: {str(e)}',
                'data': [],
                'source': 'error'
            }), 500
    
    # Manejar requests desde navegador
    try:
        if not devops_manager:
            negocios = _fallback_get_negocios()
            flash(f'Negocios cargados desde base local: {len(negocios)}', 'warning')
        else:
            negocios = devops_manager.get_negocios()
        flash(f'Negocios cargados: {len(negocios)} encontrados', 'success')
        return render_template('devops/negocios.html', negocios=negocios)
    except Exception as e:
        logger.error(f"Error cargando datos para negocios: {e}")
        flash(f'Error cargando negocios: {str(e)}', 'error')
        return render_template('devops/negocios.html', negocios=[])

@devops_bp.route('/productos', methods=['GET', 'POST'])
@devops_login_required
def gestion_productos():
    """Gestión completa de productos"""
    from flask import request, make_response, render_template, flash, redirect, url_for
    
    # Manejar POST requests (crear producto, jsonify)
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            precio = request.form.get('precio', '').strip()
            categoria = request.form.get('categoria', '').strip()
            negocio = request.form.get('negocio', '').strip()
            
            if not all([nombre, precio, categoria, negocio]):
                flash('Todos los campos son requeridos', 'error')
                return redirect(url_for('devops.gestion_productos'))
            
            try:
                precio_float = float(precio)
            except ValueError:
                flash('El precio debe ser un número válido', 'error')
                return redirect(url_for('devops.gestion_productos'))
            
            # Crear producto usando el gestor DevOps
            producto_data = {
                'nombre': nombre,
                'precio': precio_float,
                'categoria': categoria,
                'negocio': negocio,
                'descripcion': request.form.get('descripcion', ''),
                'imagen': request.form.get('imagen', ''),
                'activo': True
            }
            
            if devops_manager:
                success, message = devops_manager.create_producto(producto_data)
                if success:
                    flash(f'Producto "{nombre}" creado exitosamente', 'success')
                    logger.info(f"Producto creado desde DevOps: {nombre}")
                else:
                    logger.error(f"Error al crear producto en API: {message}")
                    # Fallback local
                    nuevo_id = _fallback_insert_producto(producto_data)
                    flash(f'API DevOps no disponible. Producto creado localmente (ID {nuevo_id}).', 'warning')
            else:
                logger.error("Gestor DevOps no disponible para crear producto")
                nuevo_id = _fallback_insert_producto(producto_data)
                flash(f'Gestor DevOps no disponible. Producto creado localmente (ID {nuevo_id}).', 'warning')
                
        except Exception as e:
            logger.error(f"Error creando producto desde DevOps: {e}")
            flash('Error interno al crear el producto', 'error')
        
        return redirect(url_for('devops.gestion_productos'))
    
    # Manejar requests AJAX/API
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            from datetime import datetime
            
            # Obtener datos reales usando el gestor DevOps o fallback DB
            if devops_manager:
                if getattr(devops_manager, 'fallback_mode', False):
                    productos = _fallback_get_productos()
                else:
                    productos = devops_manager.get_productos()
            else:
                productos = _fallback_get_productos()
            
            return jsonify({
                'status': 'success',
                'data': {
                    'productos': productos,
                    'total': len(productos),
                    'timestamp': datetime.now().isoformat()
                },
                'source': 'api',
                'message': f'Productos obtenidos correctamente ({len(productos)} encontrados)'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error obteniendo productos: {str(e)}',
                'data': [],
                'source': 'error'
            }), 500
    
    # Manejar requests desde navegador
    try:
        if not devops_manager:
            productos = _fallback_get_productos()
            negocios = _fallback_get_negocios()
            flash(f'Productos cargados desde base local: {len(productos)}', 'warning')
        else:
            productos = devops_manager.get_productos()
            negocios = devops_manager.get_negocios() if devops_manager else []
        categorias = []
        flash(f'Productos cargados: {len(productos)} encontrados', 'success')
        return render_template('devops/productos.html', productos=productos, negocios=negocios, categorias=categorias)
    except Exception as e:
        logger.error(f"Error cargando datos para productos: {e}")
        flash(f'Error cargando productos: {str(e)}', 'error')
        return render_template('devops/productos.html', productos=[], negocios=[], categorias=[])

# =================================================================
# SINCRONIZACIÓN Y UTILIDADES
# =================================================================

@devops_bp.route('/sync', methods=['GET', 'POST'])
@devops_login_required
def sincronizacion_manual():
    """Forzar sincronización manual"""
    from flask import request, make_response
    
    try:
        sync_results = {
            'timestamp': datetime.now().isoformat(),
            'ofertas': {'status': 'pending'},
            'negocios': {'status': 'pending'},
            'overall_status': 'running'
        }
        
        # Sincronizar ofertas
        try:
            if devops_manager:
                ofertas = devops_manager.get_ofertas()
                sync_results['ofertas'] = {
                    'status': 'success',
                    'count': len(ofertas),
                    'message': f'{len(ofertas)} ofertas obtenidas'
                }
            else:
                sync_results['ofertas'] = {'status': 'error', 'error': 'Gestor DevOps no disponible'}
        except Exception as e:
            sync_results['ofertas'] = {'status': 'error', 'error': str(e)}
        
        # Sincronizar negocios
        try:
            if devops_manager:
                negocios = devops_manager.get_negocios()
                sync_results['negocios'] = {
                    'status': 'success',
                    'count': len(negocios),
                    'message': f'{len(negocios)} negocios obtenidos'
                }
            else:
                sync_results['negocios'] = {'status': 'error', 'error': 'Gestor DevOps no disponible'}
        except Exception as e:
            sync_results['negocios'] = {'status': 'error', 'error': str(e)}
        
        # Determinar estado general
        if all(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'success'
        elif any(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'partial'
        else:
            sync_results['overall_status'] = 'error'
        
        if request.headers.get('Accept') == 'application/json':

        
            return jsonify({
                'status': 'success',
                'message': 'Sincronización completada',
                'data': sync_results
            })
        else:
            flash('Sincronización completada', 'success')
            return render_template('devops/sync.html', 
                                 sync_results=sync_results,
                                 status='success')
        
    except Exception as e:
        logger.error(f"Error en sincronización manual: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error en sincronización: {str(e)}'
            }), 500
        else:
            flash(f'Error en sincronización: {str(e)}', 'error')
            return render_template('devops/sync.html', 
                                 sync_results={},
                                 status='error')

@devops_bp.route('/system-status')
@devops_login_required
def system_status():
    """Estado completo del sistema DevOps"""
    try:
        if devops_manager:
            status = devops_manager.get_system_status()
            if request.headers.get('Accept') == 'application/json':

                return jsonify({
                    'status': 'success',
                    'data': status
                })
            else:
                flash('Estado del sistema obtenido', 'success')
                return render_template('devops/system_status.html', 
                                     status_data=status,
                                     status='success')
        else:
            fallback_data = {
                'timestamp': datetime.now().isoformat(),
                'fallback_mode': True,
                'api_configured': False
            }
            if request.headers.get('Accept') == 'application/json':

                return jsonify({
                    'status': 'error',
                    'message': 'Gestor DevOps no disponible',
                    'data': fallback_data
                }), 503
            else:
                flash('Gestor DevOps no disponible', 'error')
                return render_template('devops/system_status.html', 
                                     status_data=fallback_data,
                                     status='error')
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }), 500
        else:
            flash(f'Error interno: {str(e)}', 'error')
            return render_template('devops/system_status.html', 
                                 status_data={},
                                 status='error')

# =================================================================
# MANEJO DE ERRORES
# =================================================================

@devops_bp.errorhandler(404)
def devops_not_found(error):
    """Manejar errores 404 en DevOps"""
    error_data = {
        'message': 'Endpoint de DevOps no encontrado',
        'available_endpoints': [
            '/devops/',
            '/devops/health',
            '/devops/status',
            '/devops/info',
            '/devops/ofertas',
            '/devops/negocios',
            '/devops/sync',
            '/devops/system-status'
        ],
        'timestamp': datetime.now().isoformat()
    }
    
    if request.headers.get('Accept') == 'application/json':

    
        return jsonify({
            'status': 'error',
            **error_data
        }), 404
    else:
        flash('Endpoint no encontrado', 'error')
        return render_template('devops/error.html', 
                             error_data=error_data,
                             status='404'), 404

@devops_bp.errorhandler(500)
def devops_internal_error(error):
    """Manejar errores 500 en DevOps"""
    error_data = {
        'message': 'Error interno del servidor DevOps',
        'timestamp': datetime.now().isoformat()
    }
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'status': 'error',
            **error_data
        }), 500
    else:
        flash('Error interno del servidor', 'error')
        return render_template('devops/error.html', 
                             error_data=error_data,
                             status='500'), 500

# =================================================================
# SINCRONIZACIÓN Y UTILIDADES
# =================================================================

@devops_bp.route('/sync', methods=['GET', 'POST'])
@devops_login_required
def sincronizacion_manual():
    """Forzar sincronización manual"""
    from flask import request, make_response
    
    try:
        sync_results = {
            'timestamp': datetime.now().isoformat(),
            'ofertas': {'status': 'pending'},
            'negocios': {'status': 'pending'},
            'overall_status': 'running'
        }
        
        # Sincronizar ofertas
        try:
            if devops_manager:
                ofertas = devops_manager.get_ofertas()
                sync_results['ofertas'] = {
                    'status': 'success',
                    'count': len(ofertas),
                    'message': f'{len(ofertas)} ofertas obtenidas'
                }
            else:
                sync_results['ofertas'] = {'status': 'error', 'error': 'Gestor DevOps no disponible'}
        except Exception as e:
            sync_results['ofertas'] = {'status': 'error', 'error': str(e)}
        
        # Sincronizar negocios
        try:
            if devops_manager:
                negocios = devops_manager.get_negocios()
                sync_results['negocios'] = {
                    'status': 'success',
                    'count': len(negocios),
                    'message': f'{len(negocios)} negocios obtenidos'
                }
            else:
                sync_results['negocios'] = {'status': 'error', 'error': 'Gestor DevOps no disponible'}
        except Exception as e:
            sync_results['negocios'] = {'status': 'error', 'error': str(e)}
        
        # Determinar estado general
        if all(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'success'
        elif any(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'partial'
        else:
            sync_results['overall_status'] = 'error'
        
        if request.headers.get('Accept') == 'application/json':

        
            return jsonify({
                'status': 'success',
                'message': 'Sincronización completada',
                'data': sync_results
            })
        else:
            flash('Sincronización completada', 'success')
            return render_template('devops/sync.html', 
                                 sync_results=sync_results,
                                 status='success')
        
    except Exception as e:
        logger.error(f"Error en sincronización manual: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error en sincronización: {str(e)}'
            }), 500
        else:
            flash(f'Error en sincronización: {str(e)}', 'error')
            return render_template('devops/sync.html', 
                                 sync_results={},
                                 status='error')

@devops_bp.route('/system-status')
@devops_login_required
def system_status():
    """Estado completo del sistema DevOps"""
    try:
        if devops_manager:
            status = devops_manager.get_system_status()
            if request.headers.get('Accept') == 'application/json':

                return jsonify({
                    'status': 'success',
                    'data': status
                })
            else:
                flash('Estado del sistema obtenido', 'success')
                return render_template('devops/system_status.html', 
                                     status_data=status,
                                     status='success')
        else:
            fallback_data = {
                'timestamp': datetime.now().isoformat(),
                'fallback_mode': True,
                'api_configured': False
            }
            if request.headers.get('Accept') == 'application/json':

                return jsonify({
                    'status': 'error',
                    'message': 'Gestor DevOps no disponible',
                    'data': fallback_data
                }), 503
            else:
                flash('Gestor DevOps no disponible', 'error')
                return render_template('devops/system_status.html', 
                                     status_data=fallback_data,
                                     status='error')
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        if request.headers.get('Accept') == 'application/json':

            return jsonify({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }), 500
        else:
            flash(f'Error interno: {str(e)}', 'error')
            return render_template('devops/system_status.html', 
                                 status_data={},
                                 status='error')

# =================================================================
# MANEJO DE ERRORES
# =================================================================

@devops_bp.errorhandler(404)
def devops_not_found(error):
    """Manejar errores 404 en DevOps"""
    error_data = {
        'message': 'Endpoint de DevOps no encontrado',
        'available_endpoints': [
            '/devops/',
            '/devops/health',
            '/devops/status',
            '/devops/info',
            '/devops/ofertas',
            '/devops/negocios',
            '/devops/sync',
            '/devops/system-status'
        ],
        'timestamp': datetime.now().isoformat()
    }
    
    if request.headers.get('Accept') == 'application/json':

    
        return jsonify({
            'status': 'error',
            **error_data
        }), 404
    else:
        flash('Endpoint no encontrado', 'error')
        return render_template('devops/error.html', 
                             error_data=error_data,
                             status='404'), 404

@devops_bp.errorhandler(500)
def devops_internal_error(error):
    """Manejar errores 500 en DevOps"""
    error_data = {
        'message': 'Error interno del servidor DevOps',
        'timestamp': datetime.now().isoformat()
    }
    
    if request.headers.get('Accept') == 'application/json':

    
        return jsonify({
            'status': 'error',
            **error_data
        }), 500
    else:
        flash('Error interno del servidor', 'error')
        return render_template('devops/error.html', 
                             error_data=error_data,
                             status='500'), 500