import os
import json
import requests
from functools import wraps
from datetime import datetime
import logging
from urllib.parse import urljoin
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint para DevOps
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Configuración de comunicación con Belgrano Ahorro
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')  # sin default fijo
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')  
API_TIMEOUT_SECS = int(os.environ.get('API_TIMEOUT_SECS', '8'))


def get_api_base() -> str:
    """Obtiene la base de la API:
    - Si hay BELGRANO_AHORRO_URL en entorno, usa esa (y agrega /api/)
    - Si no, construye desde la request actual (request.url_root + 'api/')
    - Fallback final a http://127.0.0.1:10000/api/
    """
    env_base = os.environ.get('BELGRANO_AHORRO_URL')
    if env_base:
        return env_base.rstrip('/') + '/api/'
    try:
        # e.g. https://ticketerabelgrano.onrender.com/ -> + api/
        return urljoin(request.url_root, 'api/')
    except Exception:
        return 'http://127.0.0.1:10000/api/'


def build_api_url(path: str) -> str:
    return urljoin(get_api_base(), path.lstrip('/'))


# Credenciales DevOps (en producción deberían estar en variables de entorno)
DEVOPS_USERNAME = os.environ.get('DEVOPS_USERNAME', 'devops')
DEVOPS_PASSWORD = os.environ.get('DEVOPS_PASSWORD', 'devops2025')


def devops_required(f):
    """Decorador para verificar acceso DevOps"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('devops_authenticated'):
            return redirect(url_for('devops.login'))
        return f(*args, **kwargs)
    return decorated_function


@devops_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login específico para DevOps"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == DEVOPS_USERNAME and password == DEVOPS_PASSWORD:
            session['devops_authenticated'] = True
            session['devops_username'] = username
            flash('Acceso DevOps autorizado', 'success')
            return redirect(url_for('devops.dashboard'))
        else:
            flash('Credenciales DevOps incorrectas', 'error')

    return render_template('devops/login.html')


@devops_bp.route('/logout')
def logout():
    """Logout de DevOps"""
    session.pop('devops_authenticated', None)
    session.pop('devops_username', None)
    flash('Sesión DevOps cerrada', 'info')
    return redirect(url_for('devops.login'))


@devops_bp.route('/dashboard')
@devops_required
def dashboard():
    """Dashboard principal de DevOps"""
    try:
        # Obtener estadísticas básicas
        stats = {
            'productos_count': len(get_productos_from_belgrano()),
            'sucursales_count': len(get_sucursales_from_belgrano()),
            'ofertas_count': len(get_ofertas_from_belgrano()),
            'precios_count': len(get_precios_from_belgrano())
        }
        return render_template('devops/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error en dashboard DevOps: {e}")
        flash('Error cargando dashboard', 'error')
        return render_template('devops/dashboard.html', stats={})

# ==========================================
# ENDPOINTS DE PRODUCTOS
# ==========================================

@devops_bp.route('/productos')
@devops_required
def productos():
    """Gestión de productos"""
    try:
        productos = get_productos_from_belgrano()
        return render_template('devops/productos.html', productos=productos)
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        flash('Error cargando productos', 'error')
        return render_template('devops/productos.html', productos=[])


@devops_bp.route('/productos/agregar', methods=['POST'])
@devops_required
def agregar_producto():
    """Agregar nuevo producto"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion'),
            'precio': float(request.form.get('precio')),
            'categoria': request.form.get('categoria'),
            'stock': int(request.form.get('stock', 0)),
            'activo': True
        }
        
        response = requests.post(
            build_api_url('productos'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            flash('Producto agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando producto: {e}")
        flash('Error interno al agregar producto', 'error')
    
    return redirect(url_for('devops.productos'))


@devops_bp.route('/productos/editar/<int:id>', methods=['POST'])
@devops_required
def editar_producto(id):
    """Editar producto existente"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion'),
            'precio': float(request.form.get('precio')),
            'categoria': request.form.get('categoria'),
            'stock': int(request.form.get('stock', 0)),
            'activo': request.form.get('activo') == 'on'
        }
        
        response = requests.put(
            build_api_url(f'productos/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Producto actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando producto: {e}")
        flash('Error interno al editar producto', 'error')
    
    return redirect(url_for('devops.productos'))


@devops_bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@devops_required
def eliminar_producto(id):
    """Eliminar producto"""
    try:
        response = requests.delete(
            build_api_url(f'productos/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Producto eliminado exitosamente', 'success')
        else:
            flash(f'Error al eliminar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error eliminando producto: {e}")
        flash('Error interno al eliminar producto', 'error')
    
    return redirect(url_for('devops.productos'))

# ==========================================
# ENDPOINTS DE SUCURSALES
# ==========================================

@devops_bp.route('/sucursales')
@devops_required
def sucursales():
    """Gestión de sucursales"""
    try:
        sucursales = get_sucursales_from_belgrano()
        return render_template('devops/sucursales.html', sucursales=sucursales)
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        flash('Error cargando sucursales', 'error')
        return render_template('devops/sucursales.html', sucursales=[])


@devops_bp.route('/sucursales/agregar', methods=['POST'])
@devops_required
def agregar_sucursal():
    """Agregar nueva sucursal"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'ciudad': request.form.get('ciudad'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'activa': True
        }
        
        response = requests.post(
            build_api_url('sucursales'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            flash('Sucursal agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando sucursal: {e}")
        flash('Error interno al agregar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))


@devops_bp.route('/sucursales/editar/<int:id>', methods=['POST'])
@devops_required
def editar_sucursal(id):
    """Editar sucursal existente"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'ciudad': request.form.get('ciudad'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            build_api_url(f'sucursales/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Sucursal actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando sucursal: {e}")
        flash('Error interno al editar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))


@devops_bp.route('/sucursales/eliminar/<int:id>', methods=['POST'])
@devops_required
def eliminar_sucursal(id):
    """Eliminar sucursal"""
    try:
        response = requests.delete(
            build_api_url(f'sucursales/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Sucursal eliminada exitosamente', 'success')
        else:
            flash(f'Error al eliminar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error eliminando sucursal: {e}")
        flash('Error interno al eliminar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

# ==========================================
# ENDPOINTS DE OFERTAS
# ==========================================

@devops_bp.route('/ofertas')
@devops_required
def ofertas():
    """Gestión de ofertas"""
    try:
        ofertas = get_ofertas_from_belgrano()
        productos = get_productos_from_belgrano()
        return render_template('devops/ofertas.html', ofertas=ofertas, productos=productos)
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        flash('Error cargando ofertas', 'error')
        return render_template('devops/ofertas.html', ofertas=[], productos=[])


@devops_bp.route('/ofertas/agregar', methods=['POST'])
@devops_required
def agregar_oferta():
    """Agregar nueva oferta"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'producto_id': int(request.form.get('producto_id')),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'activa': True
        }
        
        response = requests.post(
            build_api_url('ofertas'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            flash('Oferta agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando oferta: {e}")
        flash('Error interno al agregar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))


@devops_bp.route('/ofertas/editar/<int:id>', methods=['POST'])
@devops_required
def editar_oferta(id):
    """Editar oferta existente"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'producto_id': int(request.form.get('producto_id')),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            build_api_url(f'ofertas/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Oferta actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando oferta: {e}")
        flash('Error interno al editar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))


@devops_bp.route('/ofertas/eliminar/<int:id>', methods=['POST'])
@devops_required
def eliminar_oferta(id):
    """Eliminar oferta"""
    try:
        response = requests.delete(
            build_api_url(f'ofertas/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Oferta eliminada exitosamente', 'success')
        else:
            flash(f'Error al eliminar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error eliminando oferta: {e}")
        flash('Error interno al eliminar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))

# ==========================================
# ENDPOINTS DE PRECIOS
# ==========================================

@devops_bp.route('/precios')
@devops_required
def precios():
    """Gestión de precios"""
    try:
        precios = get_precios_from_belgrano()
        return render_template('devops/precios.html', precios=precios)
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        flash('Error cargando precios', 'error')
        return render_template('devops/precios.html', precios=[])


@devops_bp.route('/precios/actualizar', methods=['POST'])
@devops_required
def actualizar_precios():
    """Actualizar precios masivamente"""
    try:
        data = request.get_json()
        cambios = data.get('cambios', [])
        
        if not cambios:
            return jsonify({'success': False, 'error': 'No hay cambios para aplicar'})
        
        # Actualizar cada precio individualmente
        for cambio in cambios:
            response = requests.put(
                build_api_url(f"productos/{cambio['id']}"),
                headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
                json={'precio': cambio['precio']},
                timeout=API_TIMEOUT_SECS
            )
            
            if response.status_code != 200:
                return jsonify({'success': False, 'error': f"Error actualizando producto {cambio['id']}"})
        
        return jsonify({'success': True, 'message': f'{len(cambios)} precios actualizados exitosamente'})
        
    except Exception as e:
        logger.error(f"Error actualizando precios: {e}")
        return jsonify({'success': False, 'error': 'Error interno al actualizar precios'})

# ==========================================
# ENDPOINTS DE NEGOCIOS
# ==========================================

@devops_bp.route('/negocios')
@devops_required
def negocios():
    """Gestión de negocios"""
    try:
        negocios = get_negocios_from_belgrano()
        return render_template('devops/negocios.html', negocios=negocios)
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        flash('Error cargando negocios', 'error')
        return render_template('devops/negocios.html', negocios=[])


@devops_bp.route('/negocios/agregar', methods=['POST'])
@devops_required
def agregar_negocio():
    """Agregar nuevo negocio"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion'),
            'categoria': request.form.get('categoria'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'activo': True
        }
        
        response = requests.post(
            build_api_url('negocios'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            flash('Negocio agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando negocio: {e}")
        flash('Error interno al agregar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))


@devops_bp.route('/negocios/editar/<int:id>', methods=['POST'])
@devops_required
def editar_negocio(id):
    """Editar negocio existente"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'descripcion': request.form.get('descripcion'),
            'categoria': request.form.get('categoria'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'activo': request.form.get('activo') == 'on'
        }
        
        response = requests.put(
            build_api_url(f'negocios/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Negocio actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando negocio: {e}")
        flash('Error interno al editar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))


@devops_bp.route('/negocios/eliminar/<int:id>', methods=['POST'])
@devops_required
def eliminar_negocio(id):
    """Eliminar negocio"""
    try:
        response = requests.delete(
            build_api_url(f'negocios/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            flash('Negocio eliminado exitosamente', 'success')
        else:
            flash(f'Error al eliminar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error eliminando negocio: {e}")
        flash('Error interno al eliminar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_productos_from_belgrano():
    """Obtener productos desde Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('productos'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        return []


def get_sucursales_from_belgrano():
    """Obtener sucursales desde Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('sucursales'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        return []


def get_ofertas_from_belgrano():
    """Obtener ofertas desde Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('ofertas'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return []


def get_precios_from_belgrano():
    """Obtener precios desde Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('precios'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        return []


def get_negocios_from_belgrano():
    """Obtener negocios desde Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('negocios'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        return []
