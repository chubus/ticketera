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
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'https://belgranoahorro-hp30.onrender.com')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')
API_TIMEOUT_SECS = 10

# Crear blueprint
devops_bp = Blueprint('devops', __name__)

# Función para construir URLs de API
def build_api_url(endpoint):
    """Construir URL completa de API"""
    return urljoin(BELGRANO_AHORRO_URL, f'/api/{endpoint}')

# Función para sincronizar cambios
def sincronizar_cambio_inmediato(tipo_cambio, datos):
    """Sincronizar cambio inmediatamente con la API"""
    try:
        logger.info(f"Sincronizando cambio: {tipo_cambio}")
        # Aquí se implementaría la lógica de sincronización
        return True
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return False

# Ruta principal de DevOps
@devops_bp.route('/')
def devops_home():
    """Panel principal de DevOps"""
    return render_template('devops/admin_panel.html')

# Ruta de gestión de ofertas
@devops_bp.route('/ofertas')
def ofertas():
    """Panel de gestión de ofertas"""
    try:
        # Intentar obtener ofertas desde la API
        response = requests.get(
            build_api_url('v1/ofertas'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            ofertas_data = response.json()
            return render_template('devops/ofertas.html', ofertas=ofertas_data)
        else:
            logger.warning(f"API respondió {response.status_code}: {response.text}")
            # Fallback: cargar desde archivo local
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                ofertas = datos.get('ofertas', {})
                return render_template('devops/ofertas.html', ofertas=ofertas)
            else:
                return render_template('devops/ofertas.html', ofertas={})
                
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return render_template('devops/ofertas.html', ofertas={})

# Ruta para agregar oferta
@devops_bp.route('/ofertas/agregar', methods=['POST'])
def agregar_oferta():
    """Agregar nueva oferta"""
    try:
        # Obtener datos del formulario
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        descuento = request.form.get('descuento')
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        
        # Validar datos
        if not all([titulo, descripcion, descuento, fecha_inicio, fecha_fin]):
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('devops.ofertas'))
        
        # Crear datos de la oferta
        oferta_data = {
            'titulo': titulo,
            'descripcion': descripcion,
            'descuento': descuento,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'activo': True,
            'creado_desde': 'devops',
            'fecha_creacion': datetime.now().isoformat()
        }
        
        # Intentar enviar a la API
        response = requests.post(
            build_api_url('v1/ofertas'),
            json=oferta_data,
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code in [200, 201]:
            flash('Oferta agregada exitosamente', 'success')
            logger.info(f"Oferta '{titulo}' agregada a la API")
            
            # Sincronizar cambio
            sincronizar_cambio_inmediato('oferta_agregada', oferta_data)
            
            return redirect(url_for('devops.ofertas'))
        else:
            logger.warning(f"API respondió {response.status_code}: {response.text}")
            flash('Error agregando oferta a la API', 'error')
            return redirect(url_for('devops.ofertas'))
            
    except Exception as e:
        logger.error(f"Error agregando oferta: {e}")
        flash('Error interno al agregar oferta', 'error')
        return redirect(url_for('devops.ofertas'))

# Ruta para eliminar oferta
@devops_bp.route('/ofertas/eliminar/<int:id>', methods=['POST'])
def eliminar_oferta(id):
    """Eliminar oferta"""
    try:
        # Intentar eliminar desde la API
        response = requests.delete(
            build_api_url(f'v1/ofertas/{id}'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Oferta eliminada exitosamente', 'success')
            logger.info(f"Oferta ID {id} eliminada de la API")
            
            # Sincronizar cambio
            sincronizar_cambio_inmediato('oferta_eliminada', {'id': id})
            
            return redirect(url_for('devops.ofertas'))
        else:
            logger.warning(f"API respondió {response.status_code}: {response.text}")
            flash('Error eliminando oferta de la API', 'error')
            return redirect(url_for('devops.ofertas'))
            
    except Exception as e:
        logger.error(f"Error eliminando oferta: {e}")
        flash('Error interno al eliminar oferta', 'error')
        return redirect(url_for('devops.ofertas'))

# Ruta de salud del sistema
@devops_bp.route('/health')
def health():
    """Health check del sistema DevOps"""
    return jsonify({
        'status': 'healthy',
        'service': 'devops',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Ruta de información del sistema
@devops_bp.route('/info')
def info():
    """Información del sistema DevOps"""
    return jsonify({
        'service': 'DevOps System',
        'description': 'Sistema de gestión DevOps para Belgrano Ahorro',
        'features': [
            'Gestión de ofertas',
            'Sincronización con API',
            'Panel de administración'
        ],
        'endpoints': {
            'ofertas': {
                'GET': '/devops/ofertas',
                'POST': '/devops/ofertas/agregar',
                'DELETE': '/devops/ofertas/eliminar/<id>'
            }
        },
        'timestamp': datetime.now().isoformat()
    })
