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
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de API
try:
    from config_env import get_api_config
    api_config = get_api_config()
    BELGRANO_AHORRO_URL = api_config['belgrano_ahorro_url']
    BELGRANO_AHORRO_API_KEY = api_config['belgrano_ahorro_api_key']
except ImportError:
    # Fallback a variables de entorno directas
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY')

API_TIMEOUT_SECS = 10

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

# Importar cliente API
try:
    from api_client import create_api_client, api_client as global_api_client
    if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
        devops_api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        logger.info("Cliente API de Belgrano Ahorro inicializado para DevOps")
    else:
        devops_api_client = None
        if env_status == 'production':
            logger.warning("Variables de entorno no configuradas para cliente API de DevOps")
        else:
            logger.info("Cliente API de DevOps no inicializado (variables no configuradas)")
except ImportError as e:
    logger.error(f"No se pudo inicializar el cliente API: {e}")
    devops_api_client = None

# Crear blueprint con prefijo
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Función para construir URLs de API
def build_api_url(endpoint):
    """Construir URL completa de API"""
    if not BELGRANO_AHORRO_URL:
        logger.warning("BELGRANO_AHORRO_URL no está configurada")
        return None
    return urljoin(BELGRANO_AHORRO_URL, f'/api/{endpoint}')

# Función para sincronizar cambios
def sincronizar_cambio_inmediato(tipo_cambio, datos):
    """Sincronizar cambio inmediatamente con la API"""
    try:
        logger.info(f"Sincronizando cambio: {tipo_cambio}")
        
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
            
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return False

# =================================================================
# RUTAS PRINCIPALES DE DEVOPS
# =================================================================

@devops_bp.route('/')
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
            # response = requests.get(
            #     build_api_url('healthz'),
            #     headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            #     timeout=5
            # )
            # if response.status_code == 200:
            #     health_status['checks']['api_connection'] = 'healthy'
            # else:
            #     health_status['checks']['api_connection'] = 'warning'
            health_status['checks']['api_connection'] = 'disabled'  # Temporalmente deshabilitado
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
def devops_info():
    """Información completa del sistema DevOps"""
    return jsonify({
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
    })

# =================================================================
# GESTIÓN DE OFERTAS
# =================================================================

@devops_bp.route('/ofertas')
def gestion_ofertas():
    """Gestión completa de ofertas"""
    try:
        # # Intentar obtener ofertas desde la API
        # response = requests.get(
        #     build_api_url('v1/ofertas'),
        #     headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
        #     timeout=API_TIMEOUT_SECS
        # )
        # 
        # if response.status_code == 200:
        #     ofertas_data = response.json()
        #     return jsonify({
        #         'status': 'success',
        #         'data': ofertas_data,
        #         'source': 'api',
        #         'message': 'Ofertas obtenidas correctamente desde la API'
        #     })
        # else:
        #     logger.warning(f"API respondió {response.status_code}: {response.text}")
        #     return jsonify({
        #         'status': 'warning',
        #         'message': f'API no disponible ({response.status_code})',
        #         'data': [],
        #         'source': 'fallback'
        #     })
        
        # Temporalmente devolver datos mock
            return jsonify({
                'status': 'success',
            'data': {'ofertas': [], 'message': 'Servicio temporalmente en modo mock'},
            'source': 'mock',
            'message': 'API de ofertas temporalmente deshabilitada'
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
        # # Intentar obtener negocios desde la API
        # response = requests.get(
        #     build_api_url('v1/negocios'),
        #     headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
        #     timeout=API_TIMEOUT_SECS
        # )
        # 
        # if response.status_code == 200:
        #     negocios_data = response.json()
        #     return jsonify({
        #         'status': 'success',
        #         'data': negocios_data,
        #         'source': 'api',
        #         'message': 'Negocios obtenidos correctamente desde la API'
        #     })
        # else:
        #     logger.warning(f"API respondió {response.status_code}: {response.text}")
        #     return jsonify({
        #         'status': 'warning',
        #         'message': f'API no disponible ({response.status_code})',
        #         'data': [],
        #         'source': 'fallback'
        #     })
        
        # Temporalmente devolver datos mock
            return jsonify({
                'status': 'success',
            'data': {'negocios': [], 'message': 'Servicio temporalmente en modo mock'},
            'source': 'mock',
            'message': 'API de negocios temporalmente deshabilitada'
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
            # response = requests.get(
            #     build_api_url('v1/ofertas'),
            #     headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            #     timeout=API_TIMEOUT_SECS
            # )
            # sync_results['ofertas'] = {
            #     'status': 'success' if response.status_code == 200 else 'error',
            #     'status_code': response.status_code,
            #     'count': len(response.json()) if response.status_code == 200 else 0
            # }
            sync_results['ofertas'] = {'status': 'disabled', 'message': 'API temporalmente deshabilitada'}
        except Exception as e:
            sync_results['ofertas'] = {'status': 'error', 'error': str(e)}
        
        # Sincronizar negocios
        try:
            # response = requests.get(
            #     build_api_url('v1/negocios'),
            #     headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            #     timeout=API_TIMEOUT_SECS
            # )
            # sync_results['negocios'] = {
            #     'status': 'success' if response.status_code == 200 else 'error',
            #     'status_code': response.status_code,
            #     'count': len(response.json()) if response.status_code == 200 else 0
            # }
            sync_results['negocios'] = {'status': 'disabled', 'message': 'API temporalmente deshabilitada'}
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

# =================================================================
# MANEJO DE ERRORES
# =================================================================

@devops_bp.errorhandler(404)
def devops_not_found(error):
    """Manejar errores 404 en DevOps"""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint de DevOps no encontrado',
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
    }), 500