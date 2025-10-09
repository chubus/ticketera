#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema DevOps Sólido para Belgrano Tickets
Proporciona gestión completa de la aplicación desde DevOps
"""

import os
import json
import requests
from functools import wraps
from datetime import datetime
import logging
from urllib.parse import urljoin
<<<<<<< HEAD
<<<<<<< HEAD
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
=======
from flask import Blueprint, request, jsonify, redirect, url_for, session, make_response, render_template
from werkzeug.security import generate_password_hash, check_password_hash
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
from flask import Blueprint, request, jsonify, redirect, url_for, session, make_response, render_template
from werkzeug.security import generate_password_hash, check_password_hash
>>>>>>> 615c446ca786e32db17288a825db5038473698d9

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
<<<<<<< HEAD
# Configuración de API
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'https://belgranoahorro-hp30.onrender.com')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')
API_TIMEOUT_SECS = 10

# Crear blueprint con prefijo
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Función para construir URLs de API
def build_api_url(endpoint):
    """Construir URL completa de API"""
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
# Configuración de API y credenciales DevOps
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY')

API_TIMEOUT_SECS = 10

# Credenciales de DevOps (propias, separadas del login de ticketera)
DEVOPS_USERNAME = os.environ.get('DEVOPS_USERNAME', 'devops')
DEVOPS_PASSWORD_PLAIN = os.environ.get('DEVOPS_PASSWORD', 'DevOps2025!Secure')

# Hash de la contraseña para comparación segura
DEVOPS_PASSWORD_HASH = generate_password_hash(DEVOPS_PASSWORD_PLAIN)

# Validar variables de entorno críticas
env_status = os.environ.get('FLASK_ENV', 'development')
if not BELGRANO_AHORRO_URL:
    if env_status != 'production':
        logger.info("BELGRANO_AHORRO_URL no configurada (normal en desarrollo)")
    else:
        logger.warning("Variable de entorno BELGRANO_AHORRO_URL no está definida")

if not BELGRANO_AHORRO_API_KEY:
    if env_status != 'production':
        logger.info("BELGRANO_AHORRO_API_KEY no configurada (normal en desarrollo)")
    else:
        logger.warning("Variable de entorno BELGRANO_AHORRO_API_KEY no está definida")

# Importar cliente API (dos estrategias)
devops_api_client = None
try:
    from api_client import create_api_client
    if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
        devops_api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        logger.info("Cliente API de Belgrano Ahorro inicializado (api_client)")
except Exception as e:
    logger.info(f"api_client no disponible: {e}")

if devops_api_client is None:
    try:
        from belgrano_client import BelgranoAhorroClient
        devops_api_client = BelgranoAhorroClient()
        logger.info("Cliente API de Belgrano Ahorro inicializado (belgrano_client)")
    except Exception as e:
        logger.warning(f"belgrano_client no disponible: {e}")
        devops_api_client = None

def api_get(path: str):
    if devops_api_client is None:
        raise RuntimeError("Cliente API no disponible")
    # Compatibilidad: ambos clientes devuelven dict JSON
    if hasattr(devops_api_client, 'get'):
        return devops_api_client.get(path)
    # BelgranoAhorroClient
    mapping = {
        'businesses': devops_api_client.get_businesses,
        'products': devops_api_client.get_products,
        'branches': devops_api_client.get_branches,
        'offers': devops_api_client.get_offers,
        'health': devops_api_client.health_check,
    }
    if path in mapping:
        return mapping[path]()
    raise ValueError(f"GET no soportado: {path}")

def api_post(path: str, data: dict):
    if devops_api_client is None:
        raise RuntimeError("Cliente API no disponible")
    if hasattr(devops_api_client, 'post'):
        return devops_api_client.post(path, json=data)
    mapping = {
        'businesses': devops_api_client.create_business,
        'products': devops_api_client.create_product,
        'branches': devops_api_client.create_branch,
        'offers': devops_api_client.create_offer,
    }
    if path in mapping:
        return mapping[path](data)
    raise ValueError(f"POST no soportado: {path}")

def api_put(path: str, item_id: int, data: dict):
    if devops_api_client is None:
        raise RuntimeError("Cliente API no disponible")
    mapping = {
        'businesses': getattr(devops_api_client, 'update_business', None),
        'products': getattr(devops_api_client, 'update_product', None),
        'branches': getattr(devops_api_client, 'update_branch', None),
        'offers': getattr(devops_api_client, 'update_offer', None),
    }
    fn = mapping.get(path)
    if fn is None:
        raise ValueError(f"PUT no soportado: {path}")
    return fn(item_id, data)

# Crear blueprint con prefijo
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# =============================
# AUTENTICACIÓN DEVOPS (PROPIA)
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
            # Redirigir directamente al login de DevOps
            logger.info("Redirigiendo a DevOps login")
            return redirect('/devops/login')
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@devops_bp.route('/login', methods=['GET', 'POST'])
def devops_login():
    """Login propio de DevOps con credenciales separadas."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == DEVOPS_USERNAME and check_password_hash(DEVOPS_PASSWORD_HASH, password):
            try:
                session['devops_authenticated'] = True
                session.permanent = True
                logger.info(f"Login exitoso de DevOps: {username}")
                return redirect(url_for('devops.devops_home'))
            except Exception as e:
                logger.error(f"Error estableciendo sesión DevOps: {e}")
                return make_response("Error interno del servidor", 500)
        else:
            logger.warning(f"Intento de login fallido de DevOps: {username}")
            # Mostrar formulario con error
            html_error = f"""
            <!doctype html>
            <html>
            <head>
                <meta charset='utf-8'>
                <title>DevOps Login - Belgrano Tickets</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h2 {{ color: #333; text-align: center; margin-bottom: 30px; }}
                    .form-group {{ margin-bottom: 20px; }}
                    label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #555; }}
                    input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
                    button {{ width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
                    button:hover {{ background: #0056b3; }}
                    .info {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #007bff; }}
                    .error {{ background: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #dc3545; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🔧 DevOps Login</h2>
                    <div class="error">
                        <strong>❌ Credenciales incorrectas</strong><br>
                        Verifique su usuario y contraseña
                    </div>
                    <div class="info">
                        <strong>Sistema DevOps</strong><br>
                        Acceso independiente para administración del sistema
                    </div>
                    <form method='post'>
                        <div class="form-group">
                            <label>Usuario DevOps:</label>
                            <input type="text" name='username' value='{username}' required />
                        </div>
                        <div class="form-group">
                            <label>Contraseña:</label>
                            <input type='password' name='password' placeholder='Ingrese su contraseña' required />
                        </div>
                        <button type='submit'>🔐 Ingresar a DevOps</button>
                    </form>
                    <div style="text-align: center; margin-top: 20px; color: #666;">
                        <small>Sistema DevOps v2.0 - Belgrano Tickets</small>
                    </div>
                </div>
            </body>
            </html>
            """
            return make_response(html_error, 401)

    # Formulario HTML mejorado para DevOps
    html = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset='utf-8'>
        <title>DevOps Login - Belgrano Tickets</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h2 {{ color: #333; text-align: center; margin-bottom: 30px; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; color: #555; }}
            input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
            button:hover {{ background: #0056b3; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #007bff; }}
            .error {{ color: #dc3545; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔧 DevOps Login</h2>
            <div class="info">
                <strong>Sistema DevOps</strong><br>
                Acceso independiente para administración del sistema
            </div>
            <form method='post'>
                <div class="form-group">
                    <label>Usuario DevOps:</label>
                    <input type="text" name='username' value='{DEVOPS_USERNAME}' required />
                </div>
                <div class="form-group">
                    <label>Contraseña:</label>
                    <input type='password' name='password' placeholder='Ingrese su contraseña' required />
                </div>
                <button type='submit'>🔐 Ingresar a DevOps</button>
            </form>
            <div style="text-align: center; margin-top: 20px; color: #666;">
                <small>Sistema DevOps v2.0 - Belgrano Tickets</small>
            </div>
        </div>
    </body>
    </html>
    """
    return make_response(html, 200)

@devops_bp.route('/logout', methods=['POST', 'GET'])
def devops_logout():
    """Cerrar sesión de DevOps"""
    try:
        session.pop('devops_authenticated', None)
        logger.info("Logout exitoso de DevOps")
        return redirect(url_for('devops.devops_login'))
    except Exception as e:
        logger.error(f"Error en logout DevOps: {e}")
        return redirect('/devops/login')

@devops_bp.route('/test')
def devops_test():
    """Endpoint de prueba para verificar que DevOps funciona"""
    from flask import request, make_response
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
        'status': 'success',
        'message': 'DevOps funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
            'authenticated': devops_is_authenticated(),
            'endpoints': {
                'health': '/devops/health',
                'status': '/devops/status',
                'ofertas': '/devops/ofertas',
                'negocios': '/devops/negocios',
                'productos': '/devops/productos',
                'precios': '/devops/precios'
            }
        })
    
    # Si no es AJAX, devolver HTML formateado
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test DevOps - Belgrano Tickets</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container { 
                max-width: 800px; 
                margin: 50px auto; 
                background: white; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 30px; 
                text-align: center; 
            }
            .content { padding: 30px; }
            .status-card {
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }
            .endpoint-list {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .endpoint-item {
                padding: 10px;
                margin: 5px 0;
                background: white;
                border-radius: 5px;
                border-left: 4px solid #667eea;
            }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
                margin: 5px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 Test DevOps</h1>
                <p>Sistema DevOps funcionando correctamente</p>
            </div>
            
            <div class="content">
                <div class="status-card">
                    <h3>✅ Sistema Operativo</h3>
                    <p>DevOps está funcionando correctamente</p>
                    <p><strong>Timestamp:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                </div>
                
                <div class="endpoint-list">
                    <h4>📋 Endpoints Disponibles</h4>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/health - Health check del sistema
                    </div>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/status - Estado detallado del sistema
                    </div>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/ofertas - Gestión de ofertas
                    </div>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/negocios - Gestión de negocios
                    </div>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/productos - Gestión de productos
                    </div>
                    <div class="endpoint-item">
                        <strong>GET</strong> /devops/precios - Gestión de precios
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/devops/" class="btn">🏠 Panel Principal</a>
                    <a href="/devops/health" class="btn">💚 Health Check</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return make_response(html, 200)

# Función para construir URLs de API
def build_api_url(endpoint):
    """Construir URL completa de API"""
    if not BELGRANO_AHORRO_URL:
        logger.warning("BELGRANO_AHORRO_URL no está configurada")
        return None
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
    return urljoin(BELGRANO_AHORRO_URL, f'/api/{endpoint}')

# Función para sincronizar cambios
def sincronizar_cambio_inmediato(tipo_cambio, datos):
    """Sincronizar cambio inmediatamente con la API"""
    try:
        logger.info(f"Sincronizando cambio: {tipo_cambio}")
<<<<<<< HEAD
<<<<<<< HEAD
        # Implementación de sincronización
        return True
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
        
        if not devops_api_client:
            logger.warning("Cliente API no disponible para sincronización")
            return False
            
        # Usar el cliente API para sincronizar
        resultado = devops_api_client.sync_data(tipo_cambio, datos)
        if resultado:
            logger.info(f"Sincronización exitosa: {tipo_cambio}")
            return True
        else:
            logger.error(f"Error en sincronización de {tipo_cambio}")
            return False
            
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return False

# =================================================================
# RUTAS PRINCIPALES DE DEVOPS
# =================================================================

@devops_bp.route('/')
<<<<<<< HEAD
<<<<<<< HEAD
def devops_home():
    """Panel principal de DevOps - Información del sistema"""
    try:
        # Obtener información del sistema
        system_info = {
            'timestamp': datetime.now().isoformat(),
            'service': 'DevOps System',
            'version': '2.0.0',
            'status': 'operational',
            'environment': {
                'python_version': os.sys.version,
                'working_directory': os.getcwd(),
                'environment_variables': {
                    'BELGRANO_AHORRO_URL': BELGRANO_AHORRO_URL,
                    'BELGRANO_AHORRO_API_KEY': '***configurada***' if BELGRANO_AHORRO_API_KEY else 'No configurada'
                }
            },
            'endpoints': {
                'health': '/devops/health',
                'info': '/devops/info',
                'status': '/devops/status',
                'ofertas': '/devops/ofertas',
                'negocios': '/devops/negocios',
                'sync': '/devops/sync',
                'logs': '/devops/logs'
            }
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Sistema DevOps funcionando correctamente',
            'data': system_info
        })
        
    except Exception as e:
        logger.error(f"Error en devops_home: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error interno: {str(e)}'
        }), 500

@devops_bp.route('/health')
def devops_health():
    """Health check completo del sistema DevOps"""
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
            response = requests.get(
                build_api_url('healthz'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=5
            )
            if response.status_code == 200:
                health_status['checks']['api_connection'] = 'healthy'
            else:
                health_status['checks']['api_connection'] = 'warning'
        except Exception as e:
            health_status['checks']['api_connection'] = 'error'
            health_status['api_error'] = str(e)
        
        return jsonify({
            'status': 'success',
            'data': health_status
        })
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error en health check: {str(e)}'
        }), 500

@devops_bp.route('/status')
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
@devops_login_required
def devops_home():
    """Panel principal de DevOps - Información del sistema"""
    from flask import request, make_response
    
    # Solo devolver JSON si se solicita explícitamente con todos los parámetros
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            # Obtener información del sistema
            system_info = {
                'timestamp': datetime.now().isoformat(),
                'service': 'DevOps System',
                'version': '2.0.0',
                'status': 'operational',
                'environment': {
                    'python_version': os.sys.version,
                    'working_directory': os.getcwd(),
                    'environment_variables': {
                        'BELGRANO_AHORRO_URL': BELGRANO_AHORRO_URL,
                        'BELGRANO_AHORRO_API_KEY': '***configurada***' if BELGRANO_AHORRO_API_KEY else 'No configurada'
                    }
                },
                'endpoints': {
                    'health': '/devops/health',
                    'info': '/devops/info',
                    'status': '/devops/status',
                    'ofertas': '/devops/ofertas',
                    'negocios': '/devops/negocios',
                    'sync': '/devops/sync',
                    'logs': '/devops/logs'
                }
            }
            
            return jsonify({
                'status': 'success',
                'message': 'Sistema DevOps funcionando correctamente',
                'data': system_info
            })
            
        except Exception as e:
            logger.error(f"Error en devops_home: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error interno: {str(e)}'
            }), 500
    
    # Si no es AJAX, devolver template HTML
    try:
        return render_template('devops/dashboard.html')
    except Exception as e:
        logger.error(f"Error cargando dashboard: {e}")
        # Fallback con HTML básico
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel DevOps - Belgrano Tickets</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 30px; 
                text-align: center; 
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.2em; opacity: 0.9; }
            .content { padding: 30px; }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 25px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-card h3 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .stat-card p {
                opacity: 0.9;
                font-size: 1.1em;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
            }
            .card h3 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.3em;
            }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
                margin: 5px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .btn-success { background: linear-gradient(135deg, #28a745, #20c997); }
            .btn-warning { background: linear-gradient(135deg, #ffc107, #e0a800); color: #212529; }
            .btn-info { background: linear-gradient(135deg, #17a2b8, #138496); }
            .btn-danger { background: linear-gradient(135deg, #dc3545, #c82333); }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-online { background: #28a745; }
            .status-offline { background: #dc3545; }
            .status-warning { background: #ffc107; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 Panel DevOps</h1>
                <p>Sistema de gestión y administración de Belgrano Tickets</p>
            </div>
            
            <div class="content">
                <div class="stats">
                    <div class="stat-card">
                        <h3 id="system-status">Online</h3>
                        <p>Estado del Sistema</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="total-endpoints">12</h3>
                        <p>Endpoints Activos</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="uptime">24h</h3>
                        <p>Tiempo Activo</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="version">v2.0</h3>
                        <p>Versión</p>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>🎯 Gestión de Contenido</h3>
                        <p>Administra ofertas, productos, negocios y precios del sistema.</p>
                        <a href="/devops/ofertas" class="btn">Gestionar Ofertas</a>
                        <a href="/devops/negocios" class="btn">Gestionar Negocios</a>
                        <a href="/devops/productos" class="btn">Gestionar Productos</a>
                        <a href="/devops/precios" class="btn">Gestionar Precios</a>
                    </div>
                    
                    <div class="card">
                        <h3>🔧 Herramientas de Desarrollo</h3>
                        <p>Herramientas para monitoreo, logs y configuración del sistema.</p>
                        <a href="/devops/logs" class="btn btn-info">Ver Logs</a>
                        <a href="/devops/config" class="btn btn-info">Configuración</a>
                        <a href="/devops/health" class="btn btn-warning">Health Check</a>
                    </div>
                    
                    <div class="card">
                        <h3>🔄 Sincronización y Datos</h3>
                        <p>Gestiona la sincronización de datos entre sistemas.</p>
                        <a href="/devops/sync" class="btn btn-success">Sincronizar Datos</a>
                        <a href="/devops/conectar-belgrano" class="btn btn-info">Conectar Belgrano Ahorro</a>
                        <button class="btn btn-warning" onclick="actualizarEstadisticas()">Actualizar Stats</button>
                    </div>
                    
                    <div class="card">
                        <h3>📊 Estado del Sistema</h3>
                        <p>Información en tiempo real del estado del sistema.</p>
                        <span class="status-indicator status-online"></span>Sistema Online<br>
                        <span class="status-indicator status-online"></span>API Conectada<br>
                        <span class="status-indicator status-online"></span>Base de Datos OK<br>
                        <button class="btn btn-info" onclick="cargarInfoSistema()">Ver Detalles</button>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="/devops/logout" class="btn btn-danger">Cerrar Sesión</a>
                </div>
            </div>
        </div>
        
        <script>
            function actualizarEstadisticas() {
                document.getElementById('uptime').textContent = '25h';
                document.getElementById('total-endpoints').textContent = '13';
                alert('Estadísticas actualizadas correctamente');
            }
            
            function cargarInfoSistema() {
                fetch('/devops/?ajax=true', {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('Sistema: ' + data.data.service + ' v' + data.data.version + '\\nEstado: ' + data.data.status);
                    }
                })
                .catch(error => {
                    alert('Error cargando información: ' + error);
                });
            }
            
            // Cargar información inicial
            cargarInfoSistema();
        </script>
    </body>
    </html>
    """
    return make_response(html, 200)

@devops_bp.route('/health')
@devops_login_required
def devops_health():
    """Health check completo del sistema DevOps"""
    from flask import request, make_response
    
    # Solo devolver JSON si se solicita explícitamente con todos los parámetros
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
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
                api_url = build_api_url('healthz')
                if api_url and BELGRANO_AHORRO_API_KEY:
                    response = requests.get(
                        api_url,
                        headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                        timeout=5
                    )
                    if response.status_code == 200:
                        health_status['checks']['api_connection'] = 'healthy'
                    else:
                        health_status['checks']['api_connection'] = 'warning'
                        health_status['api_status_code'] = response.status_code
                else:
                    health_status['checks']['api_connection'] = 'not_configured'
            except Exception as e:
                health_status['checks']['api_connection'] = 'error'
                health_status['api_error'] = str(e)
            
            return jsonify({
                'status': 'success',
                'data': health_status
            })
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error en health check: {str(e)}'
            }), 500
    
    # Si no es AJAX, devolver template HTML
    return render_template('devops/health.html')

@devops_bp.route('/status')
@devops_login_required
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
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
        
        return jsonify({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo status: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo status: {str(e)}'
        }), 500

@devops_bp.route('/info')
<<<<<<< HEAD
<<<<<<< HEAD
def devops_info():
    """Información completa del sistema DevOps"""
    return jsonify({
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
@devops_login_required
def devops_info():
    """Información completa del sistema DevOps"""
    try:
        return jsonify({
            'status': 'success',
            'message': 'Información del sistema DevOps',
            'data': {
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
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
<<<<<<< HEAD
<<<<<<< HEAD
    })
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
            }
        })
    except Exception as e:
        logger.error(f"Error obteniendo información: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo información: {str(e)}'
        }), 500

# ================================================================
# AUTENTICACIÓN (YA MANEJADA ARRIBA CON SISTEMA PROPIO)
# ================================================================
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9

# =================================================================
# GESTIÓN DE OFERTAS
# =================================================================

<<<<<<< HEAD
<<<<<<< HEAD
@devops_bp.route('/ofertas')
def gestion_ofertas():
    """Gestión completa de ofertas"""
    try:
        # Intentar obtener ofertas desde la API
        response = requests.get(
            build_api_url('v1/ofertas'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            ofertas_data = response.json()
            return jsonify({
                'status': 'success',
                'data': ofertas_data,
                'source': 'api',
                'message': 'Ofertas obtenidas correctamente desde la API'
            })
        else:
            logger.warning(f"API respondió {response.status_code}: {response.text}")
            return jsonify({
                'status': 'warning',
                'message': f'API no disponible ({response.status_code})',
                'data': [],
                'source': 'fallback'
            })
                
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo ofertas: {str(e)}',
            'data': [],
            'source': 'error'
        }), 500

@devops_bp.route('/negocios')
def gestion_negocios():
    """Gestión completa de negocios"""
    try:
        # Intentar obtener negocios desde la API
        response = requests.get(
            build_api_url('v1/negocios'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            negocios_data = response.json()
            return jsonify({
                'status': 'success',
                'data': negocios_data,
                'source': 'api',
                'message': 'Negocios obtenidos correctamente desde la API'
            })
        else:
            logger.warning(f"API respondió {response.status_code}: {response.text}")
            return jsonify({
                'status': 'warning',
                'message': f'API no disponible ({response.status_code})',
                'data': [],
                'source': 'fallback'
            })
                
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo negocios: {str(e)}',
            'data': [],
            'source': 'error'
        }), 500

# =================================================================
# SINCRONIZACIÓN Y UTILIDADES
# =================================================================

@devops_bp.route('/sync', methods=['POST'])
def sincronizacion_manual():
    """Forzar sincronización manual"""
    try:
        sync_results = {
            'timestamp': datetime.now().isoformat(),
            'ofertas': {'status': 'pending'},
            'negocios': {'status': 'pending'},
            'overall_status': 'running'
        }
        
        # Sincronizar ofertas
        try:
            response = requests.get(
                build_api_url('v1/ofertas'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=API_TIMEOUT_SECS
            )
            sync_results['ofertas'] = {
                'status': 'success' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'count': len(response.json()) if response.status_code == 200 else 0
            }
        except Exception as e:
            sync_results['ofertas'] = {'status': 'error', 'error': str(e)}
        
        # Sincronizar negocios
        try:
            response = requests.get(
                build_api_url('v1/negocios'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=API_TIMEOUT_SECS
            )
            sync_results['negocios'] = {
                'status': 'success' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'count': len(response.json()) if response.status_code == 200 else 0
            }
        except Exception as e:
            sync_results['negocios'] = {'status': 'error', 'error': str(e)}
        
        # Determinar estado general
        if all(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'success'
        elif any(item['status'] == 'success' for item in [sync_results['ofertas'], sync_results['negocios']]):
            sync_results['overall_status'] = 'partial'
        else:
            sync_results['overall_status'] = 'error'
        
        return jsonify({
            'status': 'success',
            'message': 'Sincronización completada',
            'data': sync_results
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización manual: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error en sincronización: {str(e)}'
        }), 500

@devops_bp.route('/logs')
def ver_logs():
    """Ver logs del sistema"""
    try:
        # Simular logs del sistema
        logs = [
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Sistema DevOps iniciado correctamente',
                'service': 'devops'
            },
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Blueprint de DevOps registrado',
                'service': 'app'
            },
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Conexión con API establecida',
                'service': 'api_client'
            }
        ]
        
        return jsonify({
            'status': 'success',
            'data': {
                'logs': logs,
                'total_logs': len(logs),
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo logs: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo logs: {str(e)}'
        }), 500

@devops_bp.route('/config')
def ver_configuracion():
    """Ver configuración actual del sistema"""
    try:
        config = {
            'timestamp': datetime.now().isoformat(),
            'environment': {
                'BELGRANO_AHORRO_URL': BELGRANO_AHORRO_URL,
                'BELGRANO_AHORRO_API_KEY': '***configurada***' if BELGRANO_AHORRO_API_KEY else 'No configurada',
                'API_TIMEOUT_SECS': API_TIMEOUT_SECS
            },
            'system': {
                'python_version': os.sys.version,
                'working_directory': os.getcwd(),
                'blueprint_prefix': '/devops'
            },
            'endpoints': {
                'base_url': BELGRANO_AHORRO_URL,
                'api_prefix': '/api',
                'timeout': API_TIMEOUT_SECS
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': config
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo configuración: {str(e)}'
        }), 500
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
@devops_bp.route('/ofertas', methods=['GET', 'POST'])
@devops_login_required
def gestion_ofertas():
    """Gestión completa de ofertas"""
    from flask import request, make_response, render_template, flash, redirect, url_for
    
    # Manejar POST requests (crear oferta)
    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            hasta_agotar_stock = request.form.get('hasta_agotar_stock') == 'on'
            activa = request.form.get('activa') == 'on'

            if not titulo:
                flash('Título es requerido', 'error')
                return redirect(url_for('devops.gestion_ofertas'))

            # Aceptar detalle por producto (producto_id[], precio[], stock[]) o CSV simple
            productos_detalle = []
            ids = request.form.getlist('producto_id[]')
            precios = request.form.getlist('precio[]')
            stocks = request.form.getlist('stock[]')
            if ids:
                for i, pid in enumerate(ids):
                    try:
                        productos_detalle.append({
                            'id': int(pid),
                            'precio': float(precios[i]) if i < len(precios) and precios[i] not in (None, '') else None,
                            'stock': int(stocks[i]) if i < len(stocks) and stocks[i] not in (None, '') else None,
                        })
                    except Exception:
                        continue
            else:
                productos_csv = request.form.get('productos', '').strip()
                if productos_csv:
                    for pid in [p.strip() for p in productos_csv.split(',') if p.strip()]:
                        try:
                            productos_detalle.append({'id': int(pid)})
                        except Exception:
                            continue

            from devops_persistence import get_devops_db
            db = get_devops_db()
            db.crear_oferta({
                'titulo': titulo,
                'descripcion': descripcion,
                'productos': productos_detalle,
                'hasta_agotar_stock': hasta_agotar_stock,
                'activa': activa
            })
            
            # Sincronizar con Belgrano Ahorro API
            try:
                if devops_api_client:
                    api_data = {
                        'titulo': titulo,
                        'descripcion': descripcion,
                        'productos': productos_detalle,
                        'hasta_agotar_stock': hasta_agotar_stock,
                        'activa': activa
                    }
                    api_post('offers', api_data)
                    logger.info(f"Oferta sincronizada con Belgrano Ahorro: {titulo}")
            except Exception as api_error:
                logger.warning(f"Error sincronizando oferta con API: {api_error}")

            flash(f'Oferta "{titulo}" creada exitosamente', 'success')
        except Exception as e:
            logger.error(f"Error creando oferta desde DevOps: {e}")
            flash('Error interno al crear la oferta', 'error')

        return redirect(url_for('devops.gestion_ofertas'))
    
    # Siempre devolver la interfaz HTML (no JSON) para ofertas
    
    # Si no es AJAX, devolver template HTML con datos reales
    try:
        from devops_persistence import get_devops_db
        db = get_devops_db()
        ofertas = db.obtener_ofertas()
        # Mapa de productos id->nombre para mostrar nombres en la lista
        try:
            productos = db.obtener_productos()
            productos_map = {p['id']: p.get('nombre') or p.get('name') for p in productos} if isinstance(productos, list) else {}
        except Exception:
            productos_map = {}
            
        # Devolver template con datos reales
        return render_template('devops/ofertas.html', ofertas=ofertas, productos_map=productos_map)
        
    except Exception as e:
        logger.error(f"Error cargando datos para ofertas: {e}")
        # Fallback con datos vacíos
        return render_template('devops/ofertas.html', ofertas=[], productos_map={})

# =================================================================
# NEGOCIOS (evitar 404 y permitir crear/listar con JSON)
# =================================================================

# @devops_bp.route('/negocios', methods=['GET', 'POST'])
# # @devops_login_required
# # def gestion_negocios_old():
# #     from flask import request, render_template, redirect, flash
# #     from devops_persistence import get_devops_db
#     db = get_devops_db()

#     if request.method == 'POST':
#         try:
#             nombre = request.form.get('nombre')
#             descripcion = request.form.get('descripcion') or ''
#             direccion = request.form.get('direccion') or ''
#             telefono = request.form.get('telefono') or ''
#             email = request.form.get('email') or ''
#             activo = request.form.get('activo') == 'on'
#             if not nombre:
#                 flash('Nombre es requerido', 'error')
#                 return redirect(url_for('devops.gestion_negocios'))
#             db.crear_negocio({
#                 'nombre': nombre,
#                 'descripcion': descripcion,
#                 'direccion': direccion,
#                 'telefono': telefono,
#                 'email': email,
#                 'activo': activo
#             })
#             flash('Negocio creado exitosamente', 'success')
#             return redirect(url_for('devops.gestion_negocios'))
#         except Exception as e:
#             logger.error(f"Error creando negocio: {e}")
#             flash(f'Error creando negocio: {e}', 'error')
#             return redirect(url_for('devops.gestion_negocios'))

#     # GET
#     try:
#         negocios = db.obtener_negocios()
#     except Exception:
#         negocios = []

#     # Soporte JSON para AJAX (para combos en productos/sucursales)
#     if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
#         request.args.get('ajax') == 'true' and 
#         request.args.get('format') == 'json' and 
#         request.args.get('api') == 'true' and
#         request.args.get('json') == 'true'):
#         try:
#             return jsonify({
#                 'status': 'success',
#                 'message': f'Negocios obtenidos correctamente ({len(negocios)} encontrados)',
#                 'data': {
#                     'negocios': negocios,
#                     'total': len(negocios)
#                 }
#             })
#         except Exception as e:
#             logger.error(f"Error devolviendo JSON de negocios: {e}")
#             return jsonify({'status': 'error', 'message': 'Error interno', 'data': []}), 500

#     return render_template('devops/negocios.html', negocios=negocios)

# =================================================================
# PRODUCTOS (evitar 404 y permitir crear)
# =================================================================

@devops_bp.route('/productos', methods=['GET', 'POST'])
# @devops_login_required
def gestion_productos():
    from flask import request, render_template, redirect, flash
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            precio = request.form.get('precio')
            descripcion = request.form.get('descripcion') or ''
            categoria = request.form.get('categoria') or 'General'
            stock = request.form.get('stock') or '0'
            negocio_id = request.form.get('negocio_id')

            if not nombre or not precio:
                flash('Nombre y precio son requeridos', 'error')
                return redirect(url_for('devops.gestion_productos'))

            from devops_persistence import get_devops_db
            db = get_devops_db()
            db.crear_producto({
                'nombre': nombre,
                'descripcion': descripcion,
                'precio': float(precio),
                'categoria': categoria,
                'stock': int(stock),
                'negocio_id': int(negocio_id) if negocio_id else None,
                'activo': True,
            })
            
            # Sincronizar con Belgrano Ahorro API
            try:
                if devops_api_client:
                    api_data = {
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'precio': float(precio),
                        'categoria': categoria,
                        'stock': int(stock),
                        'negocio_id': int(negocio_id) if negocio_id else None,
                        'activo': True
                    }
                    api_post('products', api_data)
                    logger.info(f"Producto sincronizado con Belgrano Ahorro: {nombre}")
            except Exception as api_error:
                logger.warning(f"Error sincronizando producto con API: {api_error}")
            
            flash('Producto creado exitosamente', 'success')
            return redirect(url_for('devops.gestion_productos'))
        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            flash(f'Error creando producto: {e}', 'error')
            return redirect(url_for('devops.gestion_productos'))

    # GET
    try:
        from devops_persistence import get_devops_db
        db = get_devops_db()
        productos = db.obtener_productos()
        negocios = db.obtener_negocios()
        categorias = db.obtener_categorias()
    except Exception:
        productos, negocios, categorias = [], [], []

    # Soporte JSON para AJAX (utilizado por otros módulos)
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            return jsonify({
                'status': 'success',
                'message': f'Productos obtenidos correctamente ({len(productos)} encontrados)',
                'data': {
                    'productos': productos,
                    'total': len(productos)
                }
            })
        except Exception as e:
            logger.error(f"Error devolviendo JSON de productos: {e}")
            return jsonify({'status': 'error', 'message': 'Error interno', 'data': []}), 500

    return render_template('devops/productos.html', productos=productos, negocios=negocios, categorias=categorias)

# =================================================================
# PRECIOS (evitar 404 y permitir actualizar)
# =================================================================

@devops_bp.route('/precios', methods=['GET', 'POST'])
# @devops_login_required
def gestion_precios():
    from flask import request, render_template, redirect, flash
    from devops_persistence import get_devops_db
    db = get_devops_db()
    if request.method == 'POST':
        try:
            producto_id = request.form.get('producto_id')
            nuevo_precio = request.form.get('nuevo_precio')
            motivo = request.form.get('motivo', '')
            if not producto_id or not nuevo_precio:
                flash('Producto y nuevo precio son requeridos', 'error')
                return redirect(url_for('devops.gestion_precios'))
            db.actualizar_precio_producto(int(producto_id), float(nuevo_precio), motivo)
            
            # Sincronizar con Belgrano Ahorro API
            try:
                if devops_api_client:
                    api_data = {
                        'producto_id': int(producto_id),
                        'nuevo_precio': float(nuevo_precio),
                        'motivo': motivo
                    }
                    api_put('products', int(producto_id), api_data)
                    logger.info(f"Precio sincronizado con Belgrano Ahorro: producto {producto_id}")
            except Exception as api_error:
                logger.warning(f"Error sincronizando precio con API: {api_error}")
            
            flash('Precio actualizado', 'success')
            return redirect(url_for('devops.gestion_precios'))
        except Exception as e:
            logger.error(f"Error actualizando precio: {e}")
            flash(f'Error actualizando precio: {e}', 'error')
            return redirect(url_for('devops.gestion_precios'))

    # GET
    precios = db.obtener_precios()
    productos = db.obtener_productos()

    # Soporte JSON para AJAX (utilizado por templates)
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            return jsonify({
                'status': 'success',
                'message': f'Precios obtenidos correctamente ({len(precios)} encontrados)',
                'data': {
                    'precios': precios,
                    'productos': productos,
                    'total': len(precios)
                }
            })
        except Exception as e:
            logger.error(f"Error devolviendo JSON de precios: {e}")
            return jsonify({'status': 'error', 'message': 'Error interno', 'data': []}), 500

    return render_template('devops/precios.html', precios=precios, productos=productos)

# =================================================================
# NEGOCIOS (evitar 404 y permitir crear/listar con JSON)
# =================================================================

@devops_bp.route('/negocios', methods=['GET', 'POST'])
@devops_login_required
def gestion_negocios():
    from flask import request, render_template, redirect, flash
    from devops_persistence import get_devops_db
    db = get_devops_db()

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion') or ''
            direccion = request.form.get('direccion') or ''
            telefono = request.form.get('telefono') or ''
            email = request.form.get('email') or ''
            activo = request.form.get('activo') == 'on'
            if not nombre:
                flash('Nombre es requerido', 'error')
                return redirect(url_for('devops.gestion_negocios'))
            db.crear_negocio({
                'nombre': nombre,
                'descripcion': descripcion,
                'direccion': direccion,
                'telefono': telefono,
                'email': email,
                'activo': activo
            })
            
            # Sincronizar con Belgrano Ahorro API
            try:
                if devops_api_client:
                    api_data = {
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'direccion': direccion,
                        'telefono': telefono,
                        'email': email,
                        'activo': activo
                    }
                    api_post('businesses', api_data)
                    logger.info(f"Negocio sincronizado con Belgrano Ahorro: {nombre}")
            except Exception as api_error:
                logger.warning(f"Error sincronizando negocio con API: {api_error}")
            
            flash('Negocio creado exitosamente', 'success')
            return redirect(url_for('devops.gestion_negocios'))
        except Exception as e:
            logger.error(f"Error creando negocio: {e}")
            flash(f'Error creando negocio: {e}', 'error')
            return redirect(url_for('devops.gestion_negocios'))

    # GET
    try:
        negocios = db.obtener_negocios()
    except Exception:
        negocios = []

    # Soporte JSON para AJAX (para combos en productos/sucursales)
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
        request.args.get('ajax') == 'true' and 
        request.args.get('format') == 'json' and 
        request.args.get('api') == 'true' and
        request.args.get('json') == 'true'):
        try:
            return jsonify({
                'status': 'success',
                'message': f'Negocios obtenidos correctamente ({len(negocios)} encontrados)',
                'data': {
                    'negocios': negocios,
                    'total': len(negocios)
                }
            })
        except Exception as e:
            logger.error(f"Error devolviendo JSON de negocios: {e}")
            return jsonify({'status': 'error', 'message': 'Error interno', 'data': []}), 500

    return render_template('devops/negocios.html', negocios=negocios)
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9

# =================================================================
# MANEJO DE ERRORES
# =================================================================

@devops_bp.errorhandler(404)
def devops_not_found(error):
    """Manejar errores 404 en DevOps"""
    return jsonify({
        'status': 'error',
<<<<<<< HEAD
<<<<<<< HEAD
        'message': 'Endpoint de DevOps no encontrado',
=======
        'message': 'Endpoint DevOps no encontrado',
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
        'message': 'Endpoint DevOps no encontrado',
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
        'available_endpoints': [
            '/devops/',
            '/devops/health',
            '/devops/status',
            '/devops/info',
            '/devops/ofertas',
            '/devops/negocios',
            '/devops/sync',
            '/devops/logs',
            '/devops/config'
        ],
        'timestamp': datetime.now().isoformat()
    }), 404

@devops_bp.errorhandler(500)
def devops_internal_error(error):
    """Manejar errores 500 en DevOps"""
    return jsonify({
        'status': 'error',
        'message': 'Error interno del servidor DevOps',
        'timestamp': datetime.now().isoformat()
<<<<<<< HEAD
<<<<<<< HEAD
    }), 500
=======
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
    }), 500

# Crear aplicación Flask para ejecución directa
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = 'devops_secret_key_2025'
    app.register_blueprint(devops_bp)
    
    print("🔧 Iniciando DevOps en puerto 5002...")
    print("📱 URL: http://localhost:5002/devops/")
    print("🔐 Credenciales: devops / DevOps2025!Secure")
    print("📝 Presiona Ctrl+C para detener")
    
    try:
        app.run(host='0.0.0.0', port=5002, debug=False)
    except KeyboardInterrupt:
        print("\n⏹️ DevOps detenido")
    except Exception as e:
        print(f"❌ Error iniciando DevOps: {e}")
<<<<<<< HEAD
>>>>>>> 4f153f9df9e6f05c23230eeb299bb9ad39dc2deb
=======
>>>>>>> 615c446ca786e32db17288a825db5038473698d9
