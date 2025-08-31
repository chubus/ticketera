import os
import json
import requests
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint para DevOps
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Configuración de comunicación con Belgrano Ahorro
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL', 'http://localhost:5000')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')

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
    """Logout DevOps"""
    session.pop('devops_authenticated', None)
    session.pop('devops_username', None)
    flash('Sesión DevOps cerrada', 'info')
    return redirect(url_for('devops.login'))

@devops_bp.route('/dashboard')
@devops_required
def dashboard():
    """Dashboard principal de DevOps"""
    try:
        # Obtener estadísticas de Belgrano Ahorro
        stats = get_belgrano_stats()
        return render_template('devops/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error en dashboard DevOps: {e}")
        flash('Error al cargar estadísticas', 'error')
        return render_template('devops/dashboard.html', stats={})

# ==========================================
# GESTIÓN DE PRODUCTOS
# ==========================================

@devops_bp.route('/productos')
@devops_required
def productos():
    """Gestión de productos"""
    try:
        productos = get_productos_from_belgrano()
        return render_template('devops/productos.html', productos=productos)
    except Exception as e:
        logger.error(f"Error cargando productos: {e}")
        flash('Error al cargar productos', 'error')
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
            f"{BELGRANO_AHORRO_URL}/api/productos",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Producto agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando producto: {e}")
        flash('Error interno al agregar producto', 'error')
    
    return redirect(url_for('devops.productos'))

@devops_bp.route('/productos/editar/<int:producto_id>', methods=['POST'])
@devops_required
def editar_producto(producto_id):
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
            f"{BELGRANO_AHORRO_URL}/api/productos/{producto_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Producto actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando producto: {e}")
        flash('Error interno al editar producto', 'error')
    
    return redirect(url_for('devops.productos'))

@devops_bp.route('/productos/eliminar/<int:producto_id>', methods=['POST'])
@devops_required
def eliminar_producto(producto_id):
    """Eliminar producto"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/productos/{producto_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE SUCURSALES
# ==========================================

@devops_bp.route('/sucursales')
@devops_required
def sucursales():
    """Gestión de sucursales"""
    try:
        sucursales = get_sucursales_from_belgrano()
        return render_template('devops/sucursales.html', sucursales=sucursales)
    except Exception as e:
        logger.error(f"Error cargando sucursales: {e}")
        flash('Error al cargar sucursales', 'error')
        return render_template('devops/sucursales.html', sucursales=[])

@devops_bp.route('/sucursales/agregar', methods=['POST'])
@devops_required
def agregar_sucursal():
    """Agregar nueva sucursal"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'ciudad': request.form.get('ciudad'),
            'activa': True
        }
        
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/sucursales",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Sucursal agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando sucursal: {e}")
        flash('Error interno al agregar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

@devops_bp.route('/sucursales/editar/<int:sucursal_id>', methods=['POST'])
@devops_required
def editar_sucursal(sucursal_id):
    """Editar sucursal existente"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'ciudad': request.form.get('ciudad'),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            f"{BELGRANO_AHORRO_URL}/api/sucursales/{sucursal_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Sucursal actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando sucursal: {e}")
        flash('Error interno al editar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

@devops_bp.route('/sucursales/eliminar/<int:sucursal_id>', methods=['POST'])
@devops_required
def eliminar_sucursal(sucursal_id):
    """Eliminar sucursal"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/sucursales/{sucursal_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE NEGOCIOS
# ==========================================

@devops_bp.route('/negocios')
@devops_required
def negocios():
    """Gestión de negocios"""
    try:
        negocios = get_negocios_from_belgrano()
        return render_template('devops/negocios.html', negocios=negocios)
    except Exception as e:
        logger.error(f"Error cargando negocios: {e}")
        flash('Error al cargar negocios', 'error')
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
            f"{BELGRANO_AHORRO_URL}/api/negocios",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Negocio agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando negocio: {e}")
        flash('Error interno al agregar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

@devops_bp.route('/negocios/editar/<int:negocio_id>', methods=['POST'])
@devops_required
def editar_negocio(negocio_id):
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
            f"{BELGRANO_AHORRO_URL}/api/negocios/{negocio_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Negocio actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando negocio: {e}")
        flash('Error interno al editar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

@devops_bp.route('/negocios/eliminar/<int:negocio_id>', methods=['POST'])
@devops_required
def eliminar_negocio(negocio_id):
    """Eliminar negocio"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/negocios/{negocio_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE OFERTAS
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
        logger.error(f"Error cargando ofertas: {e}")
        flash('Error al cargar ofertas', 'error')
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
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'producto_id': int(request.form.get('producto_id')),
            'activa': True
        }
        
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/ofertas",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Oferta agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando oferta: {e}")
        flash('Error interno al agregar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))

@devops_bp.route('/ofertas/editar/<int:oferta_id>', methods=['POST'])
@devops_required
def editar_oferta(oferta_id):
    """Editar oferta existente"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'producto_id': int(request.form.get('producto_id')),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            f"{BELGRANO_AHORRO_URL}/api/ofertas/{oferta_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Oferta actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando oferta: {e}")
        flash('Error interno al editar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))

@devops_bp.route('/ofertas/eliminar/<int:oferta_id>', methods=['POST'])
@devops_required
def eliminar_oferta(oferta_id):
    """Eliminar oferta"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/ofertas/{oferta_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE PRECIOS
# ==========================================

@devops_bp.route('/precios')
@devops_required
def precios():
    """Gestión de precios"""
    try:
        precios = get_precios_from_belgrano()
        return render_template('devops/precios.html', precios=precios)
    except Exception as e:
        logger.error(f"Error cargando precios: {e}")
        flash('Error al cargar precios', 'error')
        return render_template('devops/precios.html', precios=[])

@devops_bp.route('/precios/actualizar', methods=['POST'])
@devops_required
def actualizar_precios():
    """Actualizar precios masivamente"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/precios/actualizar-masivo",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Precios actualizados exitosamente', 'success')
            return jsonify({'success': True})
        else:
            flash(f'Error al actualizar precios: {response.text}', 'error')
            return jsonify({'success': False, 'error': response.text})
            
    except Exception as e:
        logger.error(f"Error actualizando precios: {e}")
        flash('Error interno al actualizar precios', 'error')
        return jsonify({'success': False, 'error': str(e)})

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_belgrano_stats():
    """Obtener estadísticas de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/stats",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {}

def get_productos_from_belgrano():
    """Obtener productos de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/productos",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        return []

def get_sucursales_from_belgrano():
    """Obtener sucursales de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/sucursales",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        return []

def get_negocios_from_belgrano():
    """Obtener negocios de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/negocios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        return []

def get_ofertas_from_belgrano():
    """Obtener ofertas de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/ofertas",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return []

def get_precios_from_belgrano():
    """Obtener precios de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/precios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        return []

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
    """Logout DevOps"""
    session.pop('devops_authenticated', None)
    session.pop('devops_username', None)
    flash('Sesión DevOps cerrada', 'info')
    return redirect(url_for('devops.login'))

@devops_bp.route('/dashboard')
@devops_required
def dashboard():
    """Dashboard principal de DevOps"""
    try:
        # Obtener estadísticas de Belgrano Ahorro
        stats = get_belgrano_stats()
        return render_template('devops/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error en dashboard DevOps: {e}")
        flash('Error al cargar estadísticas', 'error')
        return render_template('devops/dashboard.html', stats={})

# ==========================================
# GESTIÓN DE PRODUCTOS
# ==========================================

@devops_bp.route('/productos')
@devops_required
def productos():
    """Gestión de productos"""
    try:
        productos = get_productos_from_belgrano()
        return render_template('devops/productos.html', productos=productos)
    except Exception as e:
        logger.error(f"Error cargando productos: {e}")
        flash('Error al cargar productos', 'error')
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
            f"{BELGRANO_AHORRO_URL}/api/productos",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Producto agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando producto: {e}")
        flash('Error interno al agregar producto', 'error')
    
    return redirect(url_for('devops.productos'))

@devops_bp.route('/productos/editar/<int:producto_id>', methods=['POST'])
@devops_required
def editar_producto(producto_id):
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
            f"{BELGRANO_AHORRO_URL}/api/productos/{producto_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Producto actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar producto: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando producto: {e}")
        flash('Error interno al editar producto', 'error')
    
    return redirect(url_for('devops.productos'))

@devops_bp.route('/productos/eliminar/<int:producto_id>', methods=['POST'])
@devops_required
def eliminar_producto(producto_id):
    """Eliminar producto"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/productos/{producto_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE SUCURSALES
# ==========================================

@devops_bp.route('/sucursales')
@devops_required
def sucursales():
    """Gestión de sucursales"""
    try:
        sucursales = get_sucursales_from_belgrano()
        return render_template('devops/sucursales.html', sucursales=sucursales)
    except Exception as e:
        logger.error(f"Error cargando sucursales: {e}")
        flash('Error al cargar sucursales', 'error')
        return render_template('devops/sucursales.html', sucursales=[])

@devops_bp.route('/sucursales/agregar', methods=['POST'])
@devops_required
def agregar_sucursal():
    """Agregar nueva sucursal"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'ciudad': request.form.get('ciudad'),
            'activa': True
        }
        
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/sucursales",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Sucursal agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando sucursal: {e}")
        flash('Error interno al agregar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

@devops_bp.route('/sucursales/editar/<int:sucursal_id>', methods=['POST'])
@devops_required
def editar_sucursal(sucursal_id):
    """Editar sucursal existente"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'ciudad': request.form.get('ciudad'),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            f"{BELGRANO_AHORRO_URL}/api/sucursales/{sucursal_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Sucursal actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar sucursal: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando sucursal: {e}")
        flash('Error interno al editar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

@devops_bp.route('/sucursales/eliminar/<int:sucursal_id>', methods=['POST'])
@devops_required
def eliminar_sucursal(sucursal_id):
    """Eliminar sucursal"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/sucursales/{sucursal_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE NEGOCIOS
# ==========================================

@devops_bp.route('/negocios')
@devops_required
def negocios():
    """Gestión de negocios"""
    try:
        negocios = get_negocios_from_belgrano()
        return render_template('devops/negocios.html', negocios=negocios)
    except Exception as e:
        logger.error(f"Error cargando negocios: {e}")
        flash('Error al cargar negocios', 'error')
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
            f"{BELGRANO_AHORRO_URL}/api/negocios",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Negocio agregado exitosamente', 'success')
        else:
            flash(f'Error al agregar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando negocio: {e}")
        flash('Error interno al agregar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

@devops_bp.route('/negocios/editar/<int:negocio_id>', methods=['POST'])
@devops_required
def editar_negocio(negocio_id):
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
            f"{BELGRANO_AHORRO_URL}/api/negocios/{negocio_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Negocio actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar negocio: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando negocio: {e}")
        flash('Error interno al editar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

@devops_bp.route('/negocios/eliminar/<int:negocio_id>', methods=['POST'])
@devops_required
def eliminar_negocio(negocio_id):
    """Eliminar negocio"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/negocios/{negocio_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE OFERTAS
# ==========================================

@devops_bp.route('/ofertas')
@devops_required
def ofertas():
    """Gestión de ofertas"""
    try:
        ofertas = get_ofertas_from_belgrano()
        return render_template('devops/ofertas.html', ofertas=ofertas)
    except Exception as e:
        logger.error(f"Error cargando ofertas: {e}")
        flash('Error al cargar ofertas', 'error')
        return render_template('devops/ofertas.html', ofertas=[])

@devops_bp.route('/ofertas/agregar', methods=['POST'])
@devops_required
def agregar_oferta():
    """Agregar nueva oferta"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'producto_id': int(request.form.get('producto_id')),
            'activa': True
        }
        
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/ofertas",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 201:
            flash('Oferta agregada exitosamente', 'success')
        else:
            flash(f'Error al agregar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando oferta: {e}")
        flash('Error interno al agregar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))

@devops_bp.route('/ofertas/editar/<int:oferta_id>', methods=['POST'])
@devops_required
def editar_oferta(oferta_id):
    """Editar oferta existente"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'producto_id': int(request.form.get('producto_id')),
            'activa': request.form.get('activa') == 'on'
        }
        
        response = requests.put(
            f"{BELGRANO_AHORRO_URL}/api/ofertas/{oferta_id}",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Oferta actualizada exitosamente', 'success')
        else:
            flash(f'Error al actualizar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error editando oferta: {e}")
        flash('Error interno al editar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))

@devops_bp.route('/ofertas/eliminar/<int:oferta_id>', methods=['POST'])
@devops_required
def eliminar_oferta(oferta_id):
    """Eliminar oferta"""
    try:
        response = requests.delete(
            f"{BELGRANO_AHORRO_URL}/api/ofertas/{oferta_id}",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
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
# GESTIÓN DE PRECIOS
# ==========================================

@devops_bp.route('/precios')
@devops_required
def precios():
    """Gestión de precios"""
    try:
        precios = get_precios_from_belgrano()
        return render_template('devops/precios.html', precios=precios)
    except Exception as e:
        logger.error(f"Error cargando precios: {e}")
        flash('Error al cargar precios', 'error')
        return render_template('devops/precios.html', precios=[])

@devops_bp.route('/precios/actualizar', methods=['POST'])
@devops_required
def actualizar_precios():
    """Actualizar precios masivamente"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{BELGRANO_AHORRO_URL}/api/precios/actualizar-masivo",
            json=data,
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        
        if response.status_code == 200:
            flash('Precios actualizados exitosamente', 'success')
            return jsonify({'success': True})
        else:
            flash(f'Error al actualizar precios: {response.text}', 'error')
            return jsonify({'success': False, 'error': response.text})
            
    except Exception as e:
        logger.error(f"Error actualizando precios: {e}")
        flash('Error interno al actualizar precios', 'error')
        return jsonify({'success': False, 'error': str(e)})

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_belgrano_stats():
    """Obtener estadísticas de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/stats",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {}

def get_productos_from_belgrano():
    """Obtener productos de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/productos",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        return []

def get_sucursales_from_belgrano():
    """Obtener sucursales de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/sucursales",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
        return []

def get_negocios_from_belgrano():
    """Obtener negocios de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/negocios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
        return []

def get_ofertas_from_belgrano():
    """Obtener ofertas de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/ofertas",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
        return []

def get_precios_from_belgrano():
    """Obtener precios de Belgrano Ahorro"""
    try:
        response = requests.get(
            f"{BELGRANO_AHORRO_URL}/api/precios",
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
        return []
