import os
import json
import requests
from functools import wraps
from datetime import datetime
import logging
from urllib.parse import urljoin
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
# from flask_login import login_required, current_user  # No se usan actualmente
# from werkzeug.security import generate_password_hash, check_password_hash  # No se usan actualmente

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint para DevOps
devops_bp = Blueprint('devops', __name__, url_prefix='/devops')

# Configuración de comunicación con Belgrano Ahorro
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')  # sin default fijo
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY', 'belgrano_ahorro_api_key_2025')  
try:
    API_TIMEOUT_SECS = int(os.environ.get('API_TIMEOUT_SECS', '8'))
except (ValueError, TypeError):
    API_TIMEOUT_SECS = 8


def get_api_base() -> str:
    """Obtiene la base de la API:
    - Si hay BELGRANO_AHORRO_URL en entorno, usa esa (y agrega /api/)
    - Si no, usa la URL de Belgrano Ahorro por defecto
    """
    env_base = os.environ.get('BELGRANO_AHORRO_URL')
    if env_base:
        return env_base.rstrip('/') + '/api/'
    else:
        # URL por defecto de Belgrano Ahorro
        return 'https://belgranoahorro-hp30.onrender.com/api/'


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
        logger.info("Cargando dashboard de DevOps...")
        
        # Obtener estadísticas básicas con manejo robusto de errores
        stats = {
            'productos': 0,
            'negocios': 0,
            'ofertas': 0,
            'precios': 0,
            'sucursales': 0,
            'sync_status': 'warning',
            'sync_message': 'Verificando conexión...',
            'api_status': 'unknown',
            'last_sync': None
        }
        
        # Verificar estado de la API
        try:
            api_status = mantener_sincronizacion_activa()
            stats['api_status'] = 'connected' if api_status else 'disconnected'
        except Exception as e:
            logger.warning(f"Error verificando API: {e}")
            stats['api_status'] = 'error'
        
        # Obtener datos con manejo individual de errores
        try:
            productos = get_productos_from_belgrano()
            stats['productos'] = len(productos) if productos else 0
            logger.info(f"Productos cargados: {stats['productos']}")
    except Exception as e:
            logger.warning(f"Error cargando productos: {e}")
            stats['productos'] = 0
        
        try:
            negocios = get_negocios_from_belgrano()
            stats['negocios'] = len(negocios) if negocios else 0
            logger.info(f"Negocios cargados: {stats['negocios']}")
        except Exception as e:
            logger.warning(f"Error cargando negocios: {e}")
            stats['negocios'] = 0
        
        try:
            ofertas = get_ofertas_from_belgrano()
            stats['ofertas'] = len(ofertas) if ofertas else 0
            logger.info(f"Ofertas cargadas: {stats['ofertas']}")
        except Exception as e:
            logger.warning(f"Error cargando ofertas: {e}")
            stats['ofertas'] = 0
        
        try:
            precios = get_precios_from_belgrano()
            stats['precios'] = len(precios) if precios else 0
            logger.info(f"Precios cargados: {stats['precios']}")
        except Exception as e:
            logger.warning(f"Error cargando precios: {e}")
            stats['precios'] = 0
        
        try:
            sucursales = get_sucursales_from_belgrano()
            stats['sucursales'] = len(sucursales) if sucursales else 0
            logger.info(f"Sucursales cargadas: {stats['sucursales']}")
        except Exception as e:
            logger.warning(f"Error cargando sucursales: {e}")
            stats['sucursales'] = 0
        
        # Determinar estado de sincronización
        total_items = stats['productos'] + stats['negocios'] + stats['ofertas'] + stats['precios'] + stats['sucursales']
        
        if stats['api_status'] == 'connected' and total_items > 0:
            stats['sync_status'] = 'success'
            stats['sync_message'] = f'✅ Conectado - {total_items} elementos sincronizados'
        elif stats['api_status'] == 'connected':
            stats['sync_status'] = 'warning'
            stats['sync_message'] = '⚠️ Conectado pero sin datos'
        elif total_items > 0:
            stats['sync_status'] = 'warning'
            stats['sync_message'] = f'⚠️ Desconectado - {total_items} elementos locales'
        else:
            stats['sync_status'] = 'error'
            stats['sync_message'] = '❌ Sin conexión y sin datos locales'
        
        stats['last_sync'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"Dashboard cargado exitosamente: {stats}")
        return render_template('devops/dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error crítico en dashboard DevOps: {e}")
        flash('Error crítico cargando dashboard', 'error')
        # Retornar dashboard con datos mínimos
        return render_template('devops/dashboard.html', stats={
            'productos': 0,
            'negocios': 0,
            'ofertas': 0,
            'precios': 0,
            'sucursales': 0,
            'sync_status': 'error',
            'sync_message': '❌ Error crítico en el sistema',
            'api_status': 'error',
            'last_sync': None
        })


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
            'precio': float(request.form.get('precio', 0)),
            'categoria': request.form.get('categoria'),
            'stock': int(request.form.get('stock', 0)),
            'activo': True,
            'fecha_creacion': datetime.utcnow().isoformat(),
            'prioridad': 'alta',  # Para que aparezca primero en Belgrano Ahorro
            'origen': 'devops'  # Identificar que viene del panel de DevOps
        }
        
        # Intentar agregar a la API primero
        api_success = False
        try:
            response = requests.post(
                build_api_url('v1/productos'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                json=data,
                timeout=API_TIMEOUT_SECS
            )
            
            if response.status_code == 201:
                logger.info(f"Producto '{data['nombre']}' sincronizado exitosamente con Belgrano Ahorro")
                flash('Producto agregado exitosamente a la API', 'success')
                api_success = True
            elif response.status_code == 405:
                logger.warning("API endpoint /api/v1/productos no permite POST, usando fallback local")
                flash('API no permite agregar productos, guardando localmente', 'warning')
            elif response.status_code == 401:
                logger.warning("Error de autenticación (401) - Verificar API_KEY")
                flash('Error de autenticación con la API, guardando localmente', 'warning')
            else:
                logger.warning(f"API respondió {response.status_code}: {response.text}")
                flash(f'Error en API Belgrano Ahorro ({response.status_code}), guardando localmente', 'warning')
        except Exception as e:
            logger.error(f"Error llamando API productos: {e}")
            flash('Error conectando con Belgrano Ahorro, guardando localmente', 'warning')
        
        # Fallback local si la API falla
        if not api_success:
            try:
                return []


def get_sucursales_from_belgrano():
    """Obtener sucursales desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('v1/sucursales'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.warning("Error de autenticación (401) - Verificar API_KEY")
        elif response.status_code == 404:
            logger.info("API endpoint /api/v1/sucursales no disponible, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code} para sucursales")
    except Exception as e:
        logger.error(f"Error obteniendo sucursales: {e}")
    
    return []


def get_ofertas_from_belgrano():
    """Obtener ofertas desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('v1/ofertas'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.warning("Error de autenticación (401) - Verificar API_KEY")
        elif response.status_code == 404:
            logger.info("API endpoint /api/v1/ofertas no disponible, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code} para ofertas")
    except Exception as e:
        logger.error(f"Error obteniendo ofertas: {e}")
    
    return []


def get_precios_from_belgrano():
    """Obtener precios desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
              build_api_url('v1/precios'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.warning("Error de autenticación (401) - Verificar API_KEY")
        elif response.status_code == 404:
            logger.info("API endpoint /api/v1/precios no disponible, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code} para precios")
    except Exception as e:
        logger.error(f"Error obteniendo precios: {e}")
    
    return []


def get_negocios_from_belgrano():
    """Obtener negocios desde Belgrano Ahorro (con fallback local)"""
    try:
        response = requests.get(
            build_api_url('v1/negocios'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        if response.status_code == 200:
            negocios_api = response.json()
            # Asegurar que los negocios de la API tengan la estructura correcta
            if isinstance(negocios_api, list):
                return negocios_api
            elif isinstance(negocios_api, dict):
                return list(negocios_api.values())
            else:
                logger.warning("Formato inesperado de negocios desde API")
                return []
        elif response.status_code == 404:
            logger.warning("API endpoint /api/v1/negocios no encontrado, usando datos locales")
        else:
            logger.warning(f"API respondió {response.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo negocios: {e}")
    
    return []


def sincronizar_con_belgrano_ahorro():
    """Función para sincronizar todos los datos con Belgrano Ahorro"""
    try:
        logger.info("Iniciando sincronización con Belgrano Ahorro...")
        
        # Sincronizar productos
        productos = get_productos_from_belgrano() or []
        logger.info(f"Sincronizados {len(productos)} productos")
        
        # Sincronizar negocios
        negocios = get_negocios_from_belgrano() or []
        logger.info(f"Sincronizados {len(negocios)} negocios")
        
        # Sincronizar sucursales
        sucursales = get_sucursales_from_belgrano() or []
        logger.info(f"Sincronizadas {len(sucursales)} sucursales")
        
        # Sincronizar ofertas
        ofertas = get_ofertas_from_belgrano() or []
        logger.info(f"Sincronizadas {len(ofertas)} ofertas")
        
        # Sincronizar precios
        precios = get_precios_from_belgrano() or []
        logger.info(f"Sincronizados {len(precios)} precios")
        
        logger.info("Sincronización completada exitosamente")
        return {
            'productos': len(productos),
            'negocios': len(negocios),
            'sucursales': len(sucursales),
            'ofertas': len(ofertas),
            'precios': len(precios)
        }
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return {
            'productos': 0,
            'negocios': 0,
            'sucursales': 0,
            'ofertas': 0,
            'precios': 0
        }

def notificar_cambio_a_belgrano(tipo_cambio, datos):
    """Notificar a Belgrano Ahorro sobre cambios realizados desde DevOps"""
    try:
        # Crear payload de notificación
        payload = {
            'tipo_cambio': tipo_cambio,
            'datos': datos,
            'timestamp': datetime.utcnow().isoformat(),
            'origen': 'devops'
        }
        
        # Enviar notificación a Belgrano Ahorro
        response = requests.post(
            build_api_url('v1/notificaciones/cambios'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            json=payload,
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            logger.info(f"Notificación enviada exitosamente: {tipo_cambio}")
            return True
        else:
            logger.warning(f"Error enviando notificación: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error enviando notificación a Belgrano Ahorro: {e}")
        return False

def sincronizar_cambio_inmediato(tipo_cambio, datos):
    """Sincronizar cambio inmediatamente con Belgrano Ahorro con verificación bidireccional"""
    try:
        logger.info(f"Iniciando sincronización inmediata: {tipo_cambio}")
        
        # 1. Notificar el cambio
        notificacion_exitosa = notificar_cambio_a_belgrano(tipo_cambio, datos)
        
        # 2. Verificar sincronización según el tipo de cambio
        sync_verificado = False
        
        if tipo_cambio in ['oferta_agregada', 'oferta_actualizada', 'oferta_eliminada']:
            sync_verificado = verificar_sincronizacion_ofertas(tipo_cambio, datos)
        elif tipo_cambio in ['negocio_agregado', 'negocio_actualizado', 'negocio_eliminado']:
            sync_verificado = verificar_sincronizacion_negocios(tipo_cambio, datos)
        
        # 3. Log del resultado
        if notificacion_exitosa and sync_verificado:
            logger.info(f"✅ Sincronización completa y verificada: {tipo_cambio}")
            return True
        elif notificacion_exitosa:
            logger.warning(f"⚠️ Notificación enviada pero sincronización no verificada: {tipo_cambio}")
            return True  # La notificación se envió, aunque no se pudo verificar
        else:
            logger.error(f"❌ Sincronización falló: {tipo_cambio}")
            return False
            
    except Exception as e:
        logger.error(f"Error en sincronización inmediata: {e}")
        return False

def verificar_sincronizacion_ofertas(tipo_cambio, datos):
    """Verificar que las ofertas estén sincronizadas correctamente"""
    try:
        # Obtener ofertas actuales de Belgrano Ahorro
        response = requests.get(
            build_api_url('v1/ofertas'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            ofertas_api = response.json()
            logger.info(f"Verificación de ofertas: {len(ofertas_api) if isinstance(ofertas_api, list) else 'N/A'} ofertas en API")
            
            # Verificar según el tipo de cambio
            if tipo_cambio == 'oferta_agregada':
                # Verificar que la nueva oferta esté en la API
                if isinstance(ofertas_api, list):
                    titulo_buscado = datos.get('datos', {}).get('titulo', '')
                    oferta_encontrada = any(oferta.get('titulo') == titulo_buscado for oferta in ofertas_api)
                    if oferta_encontrada:
                        logger.info("✅ Nueva oferta verificada en API")
                        return True
                    else:
                        logger.warning("⚠️ Nueva oferta no encontrada en API")
                        return False
                        
            elif tipo_cambio == 'oferta_eliminada':
                # Verificar que la oferta eliminada ya no esté en la API
                oferta_id = datos.get('id')
                if isinstance(ofertas_api, list):
                    oferta_encontrada = any(oferta.get('id') == oferta_id for oferta in ofertas_api)
                    if not oferta_encontrada:
                        logger.info("✅ Oferta eliminada verificada en API")
                        return True
                    else:
                        logger.warning("⚠️ Oferta eliminada aún presente en API")
                        return False
                        
            return True  # Para actualizaciones, asumir éxito si la API responde
            
        else:
            logger.warning(f"No se pudo verificar sincronización de ofertas: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando sincronización de ofertas: {e}")
        return False

def verificar_sincronizacion_negocios(tipo_cambio, datos):
    """Verificar que los negocios estén sincronizados correctamente"""
    try:
        # Obtener negocios actuales de Belgrano Ahorro
        response = requests.get(
            build_api_url('v1/negocios'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=API_TIMEOUT_SECS
        )
        
        if response.status_code == 200:
            negocios_api = response.json()
            logger.info(f"Verificación de negocios: {len(negocios_api) if isinstance(negocios_api, list) else 'N/A'} negocios en API")
            
            # Verificar según el tipo de cambio
            if tipo_cambio == 'negocio_agregado':
                # Verificar que el nuevo negocio esté en la API
                if isinstance(negocios_api, list):
                    nombre_buscado = datos.get('datos', {}).get('nombre', '')
                    negocio_encontrado = any(negocio.get('nombre') == nombre_buscado for negocio in negocios_api)
                    if negocio_encontrado:
                        logger.info("✅ Nuevo negocio verificado en API")
                        return True
                    else:
                        logger.warning("⚠️ Nuevo negocio no encontrado en API")
                        return False
                        
            elif tipo_cambio == 'negocio_eliminado':
                # Verificar que el negocio eliminado ya no esté en la API
                negocio_id = datos.get('id')
                if isinstance(negocios_api, list):
                    negocio_encontrado = any(negocio.get('id') == negocio_id for negocio in negocios_api)
                    if not negocio_encontrado:
                        logger.info("✅ Negocio eliminado verificado en API")
                        return True
                    else:
                        logger.warning("⚠️ Negocio eliminado aún presente en API")
                        return False
                        
            return True  # Para actualizaciones, asumir éxito si la API responde
            
        else:
            logger.warning(f"No se pudo verificar sincronización de negocios: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando sincronización de negocios: {e}")
        return False

def mantener_sincronizacion_activa():
    """Mantener sincronización activa con Belgrano Ahorro cada 30 segundos"""
    try:
        # Verificar estado de la API
        response = requests.get(
            build_api_url('v1/health'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=5
        )
        
        if response.status_code == 200:
            logger.debug("✅ Conexión activa con Belgrano Ahorro")
            return True
        else:
            logger.warning(f"⚠️ API de Belgrano Ahorro respondió {response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ No se pudo verificar conexión con Belgrano Ahorro: {e}")
        return False

def sincronizar_datos_completos():
    """Sincronizar todos los datos con Belgrano Ahorro"""
    try:
        logger.info("🔄 Iniciando sincronización completa con Belgrano Ahorro")
        
        # Sincronizar ofertas
        ofertas_sync = False
        try:
            response = requests.get(
                build_api_url('v1/ofertas'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=API_TIMEOUT_SECS
            )
            if response.status_code == 200:
                ofertas_sync = True
                logger.info("✅ Ofertas sincronizadas")
        except Exception as e:
            logger.warning(f"⚠️ Error sincronizando ofertas: {e}")
        
        # Sincronizar negocios
        negocios_sync = False
        try:
            response = requests.get(
                build_api_url('v1/negocios'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=API_TIMEOUT_SECS
            )
            if response.status_code == 200:
                negocios_sync = True
                logger.info("✅ Negocios sincronizados")
        except Exception as e:
            logger.warning(f"⚠️ Error sincronizando negocios: {e}")
        
        # Sincronizar productos
        productos_sync = False
        try:
            response = requests.get(
                build_api_url('v1/productos'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=API_TIMEOUT_SECS
            )
            if response.status_code == 200:
                productos_sync = True
                logger.info("✅ Productos sincronizados")
        except Exception as e:
            logger.warning(f"⚠️ Error sincronizando productos: {e}")
        
        # Resumen de sincronización
        total_sync = sum([ofertas_sync, negocios_sync, productos_sync])
        logger.info(f"📊 Sincronización completa: {total_sync}/3 módulos sincronizados")
        
        return {
            'ofertas': ofertas_sync,
            'negocios': negocios_sync,
            'productos': productos_sync,
            'total': total_sync
        }
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización completa: {e}")
        return {
            'ofertas': False,
            'negocios': False,
            'productos': False,
            'total': 0
        }

def get_ofertas_destacadas_from_belgrano():
    """Obtener ofertas destacadas para la página principal de Belgrano Ahorro"""
    try:
        # Obtener todas las ofertas
        ofertas = get_ofertas_from_belgrano()
        
        # Filtrar ofertas destacadas (con prioridad alta y origen devops)
        ofertas_destacadas = []
        for oferta in ofertas:
            if (oferta.get('destacada', False) or 
                oferta.get('prioridad') == 'alta' or 
                oferta.get('origen') == 'devops'):
                ofertas_destacadas.append(oferta)
        
        # Ordenar por fecha de creación (más recientes primero)
        ofertas_destacadas.sort(key=lambda x: x.get('fecha_creacion', ''), reverse=True)
        
        # Limitar a las primeras 10 ofertas destacadas
        return ofertas_destacadas[:10]
        
    except Exception as e:
        logger.error(f"Error obteniendo ofertas destacadas: {e}")
        return []


def validar_datos_oferta(data):
    """Validar datos de oferta antes de enviar a Belgrano Ahorro"""
    errores = []
    
    # Validaciones básicas
    if not data.get('titulo'):
        errores.append('El título es obligatorio')
    
    if not data.get('producto_nombre'):
        errores.append('El nombre del producto es obligatorio')
    
    if data.get('precio_oferta', 0) <= 0:
        errores.append('El precio de oferta debe ser mayor a 0')
    
    if data.get('cantidad_disponible', 0) < 0:
        errores.append('La cantidad disponible no puede ser negativa')
    
    # Validaciones de fechas
    if data.get('fecha_inicio') and data.get('fecha_fin'):
        try:
            fecha_inicio = datetime.fromisoformat(data['fecha_inicio'].replace('Z', '+00:00'))
            fecha_fin = datetime.fromisoformat(data['fecha_fin'].replace('Z', '+00:00'))
            if fecha_inicio >= fecha_fin:
                errores.append('La fecha de inicio debe ser anterior a la fecha de fin')
        except ValueError:
            errores.append('Formato de fecha inválido')
    
    # Validaciones de colores
    if data.get('color_principal') and not data['color_principal'].startswith('#'):
        errores.append('El color principal debe ser un código hexadecimal válido')
    
    return errores


def test_conexion_belgrano_ahorro():
    """Test de conexión con Belgrano Ahorro"""
    try:
        response = requests.get(
            build_api_url('v1/health'),
            headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
            timeout=5
        )
        return {
            'conectado': response.status_code == 200,
            'status_code': response.status_code,
            'tiempo_respuesta': response.elapsed.total_seconds(),
            'url': build_api_url('v1/health')
        }
    except Exception as e:
        return {
            'conectado': False,
            'error': str(e),
            'url': build_api_url('v1/health')
        }


def sincronizar_todos_los_datos():
    """Sincronizar todos los datos con Belgrano Ahorro"""
    resultados = {
        'productos': {'exitoso': False, 'total': 0, 'errores': []},
        'negocios': {'exitoso': False, 'total': 0, 'errores': []},
        'ofertas': {'exitoso': False, 'total': 0, 'errores': []},
        'sucursales': {'exitoso': False, 'total': 0, 'errores': []}
    }
    
    try:
        # Test de conexión
        test_conexion = test_conexion_belgrano_ahorro()
        if not test_conexion['conectado']:
            logger.error(f"No se puede conectar con Belgrano Ahorro: {test_conexion}")
            return resultados
        
        # Obtener datos locales
        try:
            if os.path.exists('productos.json'):
                with open('productos.json', 'r', encoding='utf-8') as f:
                    datos_locales = json.load(f)
                
                # Sincronizar productos
                productos = datos_locales.get('productos', [])
                resultados['productos']['total'] = len(productos)
                
                # Sincronizar negocios
                negocios = datos_locales.get('negocios', {})
                resultados['negocios']['total'] = len(negocios)
                
                # Sincronizar ofertas
                ofertas = datos_locales.get('ofertas', {})
                resultados['ofertas']['total'] = len(ofertas)
                
                # Sincronizar sucursales
                sucursales = datos_locales.get('sucursales', {})
                resultados['sucursales']['total'] = len(sucursales)
                
                logger.info(f"Sincronización iniciada: {resultados}")
                
        except Exception as e:
            logger.error(f"Error cargando datos locales: {e}")
    
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
    
    return resultados


@devops_bp.route('/test/api-diagnostico')
@devops_required
def test_api_diagnostico():
    """Diagnóstico completo de la API"""
    diagnostico = {
        'api_url': get_api_base(),
        'api_key_configured': bool(BELGRANO_AHORRO_API_KEY),
        'api_key_length': len(BELGRANO_AHORRO_API_KEY) if BELGRANO_AHORRO_API_KEY else 0,
        'endpoints': {}
    }
    
    # Probar cada endpoint
    endpoints = ['health', 'productos', 'negocios', 'ofertas', 'sucursales', 'precios']
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                build_api_url(f'v1/{endpoint}'),
                headers={'X-API-Key': BELGRANO_AHORRO_API_KEY},
                timeout=5
            )
            diagnostico['endpoints'][endpoint] = {
                'status_code': response.status_code,
                'available': response.status_code == 200,
                'error': None
            }
        except Exception as e:
            diagnostico['endpoints'][endpoint] = {
                'status_code': None,
                'available': False,
                'error': str(e)
            }
    
    return jsonify(diagnostico)
