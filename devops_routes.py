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
            'productos': len(get_productos_from_belgrano()),
            'negocios': len(get_negocios_from_belgrano()),
            'ofertas': len(get_ofertas_from_belgrano()),
            'precios': len(get_precios_from_belgrano()),
            'sucursales': len(get_sucursales_from_belgrano())
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
            'activo': True,
            'fecha_creacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        response = requests.post(
            build_api_url('productos'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            logger.info(f"Producto '{data['nombre']}' sincronizado exitosamente con Belgrano Ahorro")
            flash('Producto agregado exitosamente y sincronizado con Belgrano Ahorro', 'success')
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
            'activo': request.form.get('activo') == 'on',
            'fecha_modificacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        response = requests.put(
            build_api_url(f'productos/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            logger.info(f"Producto ID {id} actualizado y sincronizado con Belgrano Ahorro")
            flash('Producto actualizado exitosamente y sincronizado con Belgrano Ahorro', 'success')
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
    """Agregar nueva sucursal (con fallback local)"""
    try:
        data = {
            'nombre': request.form.get('nombre'),
            'direccion': request.form.get('direccion'),
            'ciudad': request.form.get('ciudad'),
            'telefono': request.form.get('telefono'),
            'email': request.form.get('email'),
            'activa': True,
            'fecha_creacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        # Intentar agregar a la API primero
        try:
            response = requests.post(
                build_api_url('sucursales'),
                headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
                json=data,
                timeout=API_TIMEOUT_SECS
            )
            
            if response.status_code == 201:
                logger.info(f"Sucursal '{data['nombre']}' sincronizada exitosamente con Belgrano Ahorro")
                flash('Sucursal agregada exitosamente y sincronizada con Belgrano Ahorro', 'success')
                return redirect(url_for('devops.sucursales'))
            elif response.status_code == 404:
                logger.warning("API endpoint /api/sucursales no encontrado, usando fallback local")
            else:
                logger.warning(f"API respondió {response.status_code}: {response.text}")
                flash(f'Error en API Belgrano Ahorro ({response.status_code}), guardando localmente', 'warning')
        except Exception as e:
            logger.error(f"Error llamando API sucursales: {e}")
            flash('Error conectando con Belgrano Ahorro, guardando localmente', 'warning')
        
        # Fallback local: guardar en productos.json
        try:
            # Cargar datos existentes
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos = json.load(f)
            else:
                datos = {'productos': [], 'sucursales': {}, 'ofertas': {}, 'negocios': {}, 'categorias': {}}
            
            # Agrupar sucursales por negocio (usar 'default' si no se especifica)
            negocio_id = request.form.get('negocio_id') or 'default'
            datos.setdefault('sucursales', {})
            datos['sucursales'].setdefault(negocio_id, {})
            
            # Generar ID único para la sucursal
            sucursal_id = str(int(datetime.utcnow().timestamp()*1000))
            
            # Crear la sucursal
            datos['sucursales'][negocio_id][sucursal_id] = {
                'id': sucursal_id,
                'nombre': data['nombre'],
                'direccion': data.get('direccion'),
                'ciudad': data.get('ciudad'),
                'telefono': data.get('telefono'),
                'email': data.get('email'),
                'activa': True,
                'fecha_creacion': datetime.utcnow().isoformat(),
                'negocio_id': negocio_id
            }
            
            # Guardar en productos.json
            with open('productos.json', 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            
            flash('Sucursal agregada localmente (fallback)', 'success')
            logger.info(f"Sucursal '{data['nombre']}' agregada localmente con ID: {sucursal_id}")
            
        except Exception as e:
            logger.error(f"Error guardando sucursal localmente: {e}")
            flash('Error guardando sucursal localmente', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando sucursal: {e}")
        flash('Error interno al agregar sucursal', 'error')
    
    return redirect(url_for('devops.sucursales'))

# ==========================================
# ENDPOINTS DE OFERTAS
# ==========================================

@devops_bp.route('/ofertas')
@devops_required
def ofertas():
    """Gestión de ofertas con texto libre para productos"""
    try:
        logger.info("Accediendo a página de ofertas")
        
        # Intentar obtener ofertas con manejo robusto de errores
        ofertas = []
        try:
            ofertas = get_ofertas_from_belgrano()
            logger.info(f"Ofertas obtenidas: {len(ofertas)}")
        except Exception as api_error:
            logger.warning(f"Error obteniendo ofertas de API: {api_error}")
            # Continuar con lista vacía
        
        # Verificar que ofertas es una lista válida
        if not isinstance(ofertas, list):
            logger.warning("Ofertas no es una lista, convirtiendo a lista vacía")
            ofertas = []
        
        return render_template('devops/ofertas_fix.html', ofertas=ofertas)
        
    except Exception as e:
        logger.error(f"Error crítico en página de ofertas: {e}")
        flash('Error cargando ofertas', 'error')
        # Retornar página con lista vacía
        return render_template('devops/ofertas_fix.html', ofertas=[])


@devops_bp.route('/ofertas/agregar', methods=['POST'])
@devops_required
def agregar_oferta():
    """Agregar nueva oferta con nombre de producto en texto libre"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'producto_nombre': request.form.get('producto_nombre'),  # Nombre del producto en texto libre
            'producto_id': request.form.get('producto_id', ''),  # Opcional
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'activa': True,
            'fecha_creacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        response = requests.post(
            build_api_url('ofertas'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 201:
            logger.info(f"Oferta '{data['titulo']}' sincronizada exitosamente con Belgrano Ahorro")
            flash('Oferta agregada exitosamente y sincronizada con Belgrano Ahorro', 'success')
        else:
            flash(f'Error al agregar oferta: {response.text}', 'error')
            
    except Exception as e:
        logger.error(f"Error agregando oferta: {e}")
        flash('Error interno al agregar oferta', 'error')
    
    return redirect(url_for('devops.ofertas'))


@devops_bp.route('/ofertas/editar/<int:id>', methods=['POST'])
@devops_required
def editar_oferta(id):
    """Editar oferta existente con nombre de producto en texto libre"""
    try:
        data = {
            'titulo': request.form.get('titulo'),
            'descripcion': request.form.get('descripcion'),
            'descuento': float(request.form.get('descuento')),
            'producto_nombre': request.form.get('producto_nombre'),  # Nombre del producto en texto libre
            'producto_id': request.form.get('producto_id', ''),  # Opcional
            'fecha_inicio': request.form.get('fecha_inicio'),
            'fecha_fin': request.form.get('fecha_fin'),
            'activa': request.form.get('activa') == 'on',
            'fecha_modificacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        response = requests.put(
            build_api_url(f'ofertas/{id}'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            logger.info(f"Oferta ID {id} actualizada y sincronizada con Belgrano Ahorro")
            flash('Oferta actualizada exitosamente y sincronizada con Belgrano Ahorro', 'success')
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

@devops_bp.route('/productos/gestión-avanzada')
@devops_required
def gestion_avanzada_productos():
    """Gestión avanzada de productos de todos los negocios"""
    try:
        # Obtener todos los productos desde Belgrano Ahorro
        productos = get_productos_from_belgrano()
        negocios = get_negocios_from_belgrano()
        
        return render_template('devops/gestion_avanzada_productos.html', 
                             productos=productos, negocios=negocios)
    except Exception as e:
        logger.error(f"Error en gestión avanzada de productos: {e}")
        flash('Error cargando gestión avanzada de productos', 'error')
        return render_template('devops/gestion_avanzada_productos.html', 
                             productos=[], negocios=[])

@devops_bp.route('/productos/actualizar-detalle', methods=['POST'])
@devops_required
def actualizar_detalle_producto():
    """Actualizar detalles completos de un producto"""
    try:
        data = request.get_json()
        producto_id = data.get('id')
        
        if not producto_id:
            return jsonify({'success': False, 'error': 'ID de producto requerido'})
        
        # Preparar datos para actualización
        update_data = {
            'nombre': data.get('nombre'),
            'descripcion': data.get('descripcion'),
            'precio': float(data.get('precio', 0)),
            'stock': int(data.get('stock', 0)),
            'categoria': data.get('categoria'),
            'activo': data.get('activo', True),
            'modificado_desde': 'devops'
        }
        
        # Actualizar producto
        response = requests.put(
            build_api_url(f"productos/{producto_id}"),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            json=update_data,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Producto actualizado exitosamente'})
        else:
            return jsonify({'success': False, 'error': f'Error actualizando producto: {response.text}'})
        
    except Exception as e:
        logger.error(f"Error actualizando detalle de producto: {e}")
        return jsonify({'success': False, 'error': 'Error interno al actualizar producto'})

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
            'activo': True,
            'fecha_creacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        # Intentar agregar a la API primero
        try:
            response = requests.post(
                build_api_url('v1/negocios'),
                headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
                json=data,
                timeout=API_TIMEOUT_SECS
            )
            
            if response.status_code == 201:
                logger.info(f"Negocio '{data['nombre']}' sincronizado exitosamente con Belgrano Ahorro")
                flash('Negocio agregado exitosamente y sincronizado con Belgrano Ahorro', 'success')
                return redirect(url_for('devops.negocios'))
            elif response.status_code == 404:
                logger.warning("API endpoint /api/v1/negocios no encontrado, usando fallback local")
            else:
                logger.warning(f"API respondió {response.status_code}: {response.text}")
                flash(f'Error en API Belgrano Ahorro ({response.status_code}), guardando localmente', 'warning')
        except Exception as e:
            logger.error(f"Error llamando API negocios: {e}")
            flash('Error conectando con Belgrano Ahorro, guardando localmente', 'warning')
        
        # Fallback local: guardar en productos.json
        try:
            # Cargar datos existentes
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos = json.load(f)
            else:
                datos = {'productos': [], 'sucursales': {}, 'ofertas': {}, 'negocios': {}, 'categorias': {}}
            
            # Generar ID único para el negocio
            negocio_id = str(int(datetime.utcnow().timestamp()*1000))
            
            # Crear el negocio
            datos.setdefault('negocios', {})
            datos['negocios'][negocio_id] = {
                'id': negocio_id,
                'nombre': data['nombre'],
                'descripcion': data.get('descripcion'),
                'categoria': data.get('categoria'),
                'direccion': data.get('direccion'),
                'telefono': data.get('telefono'),
                'email': data.get('email'),
                'activo': True,
                'fecha_creacion': datetime.utcnow().isoformat(),
                'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
                'origen': 'devops'  # Identificar que viene del panel de DevOps
            }
            
            # Guardar en productos.json
            with open('productos.json', 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            
            flash('Negocio agregado localmente (fallback)', 'success')
            logger.info(f"Negocio '{data['nombre']}' agregado localmente con ID: {negocio_id}")
            
        except Exception as e:
            logger.error(f"Error guardando negocio localmente: {e}")
            flash('Error guardando negocio localmente', 'error')
            
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
            'activo': request.form.get('activo') == 'on',
            'fecha_modificacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        # Intentar actualizar en la API primero
        try:
            response = requests.put(
                build_api_url(f'v1/negocios/{id}'),
                headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
                json=data,
                timeout=API_TIMEOUT_SECS
            )
            
            if response.status_code == 200:
                logger.info(f"Negocio ID {id} actualizado y sincronizado con Belgrano Ahorro")
                flash('Negocio actualizado exitosamente y sincronizado con Belgrano Ahorro', 'success')
                return redirect(url_for('devops.negocios'))
            elif response.status_code == 404:
                logger.warning("API endpoint /api/v1/negocios no encontrado, usando fallback local")
            else:
                logger.warning(f"API respondió {response.status_code}: {response.text}")
                flash(f'Error en API Belgrano Ahorro ({response.status_code}), actualizando localmente', 'warning')
        except Exception as e:
            logger.error(f"Error llamando API negocios: {e}")
            flash('Error conectando con Belgrano Ahorro, actualizando localmente', 'warning')
        
        # Fallback local: actualizar en productos.json
        try:
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos_json = json.load(f)
                
                if 'negocios' in datos_json and str(id) in datos_json['negocios']:
                    datos_json['negocios'][str(id)].update({
                        'nombre': data['nombre'],
                        'descripcion': data.get('descripcion'),
                        'categoria': data.get('categoria'),
                        'direccion': data.get('direccion'),
                        'telefono': data.get('telefono'),
                        'email': data.get('email'),
                        'activo': data.get('activo', True),
                        'fecha_modificacion': datetime.utcnow().isoformat()
                    })
                    
                    with open('productos.json', 'w', encoding='utf-8') as f:
                        json.dump(datos_json, f, ensure_ascii=False, indent=2)
                    
                    flash('Negocio actualizado localmente (fallback)', 'success')
                    logger.info(f"Negocio ID {id} actualizado localmente")
                else:
                    flash('Negocio no encontrado', 'error')
            else:
                flash('No hay datos locales disponibles', 'error')
                
        except Exception as e:
            logger.error(f"Error actualizando negocio localmente: {e}")
            flash('Error actualizando negocio localmente', 'error')
            
    except Exception as e:
        logger.error(f"Error editando negocio: {e}")
        flash('Error interno al editar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))


@devops_bp.route('/negocios/eliminar/<int:id>', methods=['POST'])
@devops_required
def eliminar_negocio(id):
    """Eliminar negocio"""
    try:
        # Intentar eliminar en la API primero
        try:
            response = requests.delete(
                build_api_url(f'v1/negocios/{id}'),
                headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
                timeout=API_TIMEOUT_SECS
            )

            if response.status_code == 200:
                flash('Negocio eliminado exitosamente de la API', 'success')
                return redirect(url_for('devops.negocios'))
            elif response.status_code == 404:
                logger.warning("API endpoint /api/v1/negocios no encontrado, usando fallback local")
            else:
                logger.warning(f"API respondió {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error llamando API negocios: {e}")
        
        # Fallback local: eliminar de productos.json
        try:
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos_json = json.load(f)
                
                if 'negocios' in datos_json and str(id) in datos_json['negocios']:
                    negocio_nombre = datos_json['negocios'][str(id)].get('nombre', 'Sin nombre')
                    del datos_json['negocios'][str(id)]
                    
                    with open('productos.json', 'w', encoding='utf-8') as f:
                        json.dump(datos_json, f, ensure_ascii=False, indent=2)
                    
                    flash(f'Negocio "{negocio_nombre}" eliminado localmente (fallback)', 'success')
                    logger.info(f"Negocio ID {id} eliminado localmente")
                else:
                    flash('Negocio no encontrado', 'error')
            else:
                flash('No hay datos locales disponibles', 'error')
                
        except Exception as e:
            logger.error(f"Error eliminando negocio localmente: {e}")
            flash('Error eliminando negocio localmente', 'error')
            
    except Exception as e:
        logger.error(f"Error eliminando negocio: {e}")
        flash('Error interno al eliminar negocio', 'error')
    
    return redirect(url_for('devops.negocios'))

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_productos_from_belgrano():
    """Obtener productos desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('productos'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("API endpoint /api/productos no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
    
    # Fallback local: cargar desde productos.json
    try:
        if os.path.exists('productos.json'):
            with open('productos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            return datos.get('productos', [])
    except Exception as e:
        logger.error(f"Error cargando productos locales: {e}")
    
    return []


def get_sucursales_from_belgrano():
    """Obtener sucursales desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('sucursales'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("API endpoint /api/sucursales no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
    
    # Fallback local: cargar desde productos.json
    try:
        if os.path.exists('productos.json'):
            with open('productos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            sucursales = datos.get('sucursales', {})
            # Convertir a lista plana para el template
            plano = []
            for negocio_id, sucs in sucursales.items():
                for s_id, s in sucs.items():
                    plano.append(s)
            return plano
    except Exception as e:
        logger.error(f"Error cargando sucursales locales: {e}")
    
    return []


def get_ofertas_from_belgrano():
    """Obtener ofertas desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('ofertas'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("API endpoint /api/ofertas no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
    
    # Fallback local: cargar desde productos.json
    try:
        if os.path.exists('productos.json'):
            with open('productos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            ofertas = datos.get('ofertas', {})
            # Convertir a lista para el template
            return list(ofertas.values())
    except Exception as e:
        logger.error(f"Error cargando ofertas locales: {e}")
    
        return []


def get_precios_from_belgrano():
    """Obtener precios desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('precios'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("API endpoint /api/precios no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
    
    # Fallback local: cargar desde productos.json
    try:
        if os.path.exists('productos.json'):
            with open('productos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            # Los precios están en los productos, extraer solo los precios
            productos = datos.get('productos', [])
            precios = [{"id": p.get("id"), "nombre": p.get("nombre"), "precio": p.get("precio")} for p in productos if p.get("precio")]
            return precios
    except Exception as e:
        logger.error(f"Error cargando precios locales: {e}")
    
        return []


def get_negocios_from_belgrano():
    """Obtener negocios desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('v1/negocios'),
            headers={'Authorization': f'Bearer {BELGRANO_AHORRO_API_KEY}'},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning("API endpoint /api/v1/negocios no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
    
    # Fallback local: cargar desde productos.json
    try:
        if os.path.exists('productos.json'):
            with open('productos.json', 'r', encoding='utf-8') as f:
                datos = json.load(f)
            negocios = datos.get('negocios', {})
            # Convertir a lista para el template
            return list(negocios.values())
    except Exception as e:
        logger.error(f"Error cargando negocios locales: {e}")
    
        return []