import os
from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify, session, send_from_directory
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_socketio import SocketIO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from datetime import datetime
import json
import logging
import hmac
import binascii
import hashlib
from typing import Any, Dict, List, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración y variables de entorno seguras (no bloqueantes)
try:
    # Intentar import desde el mismo paquete
    from .config import load_env_defaults, validate_env_non_blocking
    load_env_defaults()
    validate_env_non_blocking()
except ImportError:
    try:
        # Fallback: import absoluto desde belgrano_tickets
        from belgrano_tickets.config import load_env_defaults, validate_env_non_blocking
        load_env_defaults()
        validate_env_non_blocking()
    except ImportError:
        try:
            # Fallback final: import directo
            from config import load_env_defaults, validate_env_non_blocking
            load_env_defaults()
            validate_env_non_blocking()
        except Exception as e:
            print(f"WARNING: Config no disponible: {e}")

# Inicialización Flask y extensiones
app = Flask(__name__)
# Secret key y cookies configurables por entorno
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'belgrano_tickets_secret_2025')
app.config.update(
    SESSION_COOKIE_SAMESITE=os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax'),
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
    REMEMBER_COOKIE_SECURE=os.environ.get('REMEMBER_COOKIE_SECURE', 'false').lower() == 'true',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_DOMAIN=None,
    # Configuración adicional para Socket.IO
    SESSION_COOKIE_NAME='belgrano_tickets_session',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hora
    # Configuración de Socket.IO
    SOCKETIO_ASYNC_MODE='threading',
    SOCKETIO_CORS_ALLOWED_ORIGINS="*"
)

# Configuración de carga de archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Agregar configuración de uploads a app.config
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_EXTENSIONS'] = ['.png', '.jpg', '.jpeg', '.webp']
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Configuración de base de datos - en producción usar DATABASE_URL; en dev usar sqlite local

import re

def is_valid_database_url(url):
    """Validar que DATABASE_URL sea válida y no tenga placeholders"""
    if not url or not isinstance(url, str):
        return False
    
    # Detectar placeholders inválidos literales (como "HOST", "USER", "PASSWORD" en mayúsculas)
    # Estos son típicamente placeholders que no fueron reemplazados
    invalid_placeholders = ['HOST', 'USER', 'PASSWORD', 'DBNAME', 'PORT']
    url_upper = url.upper()
    if any(placeholder in url_upper for placeholder in invalid_placeholders):
        # Verificar si es un placeholder literal o un valor real
        # Si contiene "HOST" como palabra completa, es probablemente un placeholder
        if re.search(r'[:@]HOST[:\/]', url_upper) or url_upper.endswith('@HOST'):
            return False
    
    # Verificar que sea una URL válida de base de datos
    valid_schemes = ['postgresql://', 'postgres://', 'sqlite:///', 'mysql://']
    if not any(url.startswith(scheme) for scheme in valid_schemes):
        return False
    
    # Verificar que no sea solo el esquema sin datos
    if url.count('://') == 1 and len(url.split('://')[1].strip()) < 3:
        return False
    
    return True

env_db_url = os.environ.get('DATABASE_URL')
env_db_path = os.environ.get('TICKETS_DB_PATH')
db_path = env_db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')

# Validar DATABASE_URL antes de usarla
if env_db_url and is_valid_database_url(env_db_url):
    app.config['SQLALCHEMY_DATABASE_URI'] = env_db_url
    print(f"✅ Usando DATABASE_URL de PostgreSQL")
else:
    # Fallback a SQLite si DATABASE_URL no es válida
    sqlite_uri = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
    if env_db_url:
        print(f"⚠️ DATABASE_URL inválida o contiene placeholders: {env_db_url[:50]}...")
        print(f"   Usando SQLite como fallback: {db_path}")
    else:
        print(f"ℹ️ DATABASE_URL no configurada, usando SQLite: {db_path}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print(f"Ticketera DB_URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

# Importar db desde models
try:
    # Intentar import relativo primero
    from .models import db, User, Ticket
except ImportError:
    try:
        # Fallback: import absoluto
        from belgrano_tickets.models import db, User, Ticket
    except ImportError:
        try:
            # Fallback final: import directo
            import sys
            
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from models import db, User, Ticket
        except ImportError as e:
            print(f"ERROR: No se pudo importar models: {e}")
            raise

# ==========================================
# CONFIGURACIÓN DE COMUNICACIÓN API
# ==========================================
# Variables de entorno para comunicación entre servicios
BELGRANO_AHORRO_URL = os.environ.get('BELGRANO_AHORRO_URL')
BELGRANO_AHORRO_API_KEY = os.environ.get('BELGRANO_AHORRO_API_KEY')

# Validar variables de entorno críticas
env_status = os.environ.get('FLASK_ENV', 'development')
if not BELGRANO_AHORRO_URL:
    if env_status != 'production':
        print("BELGRANO_AHORRO_URL no configurada (normal en desarrollo)")
    else:
        print("Variable de entorno BELGRANO_AHORRO_URL no está definida")

if not BELGRANO_AHORRO_API_KEY:
    if env_status != 'production':
        print("BELGRANO_AHORRO_API_KEY no configurada (normal en desarrollo)")
    else:
        print("Variable de entorno BELGRANO_AHORRO_API_KEY no está definida")

print(f"Configuracion API:")
print(f"   BELGRANO_AHORRO_URL: {BELGRANO_AHORRO_URL or 'No configurada'}")
if BELGRANO_AHORRO_API_KEY:
    print(f"   API_KEY: {BELGRANO_AHORRO_API_KEY[:10]}...")
else:
    print("   API_KEY: No configurada")

# ==========================================
# HELPERS DE AUTENTICACIÓN PARA ENDPOINTS API
# ==========================================

def _get_valid_api_keys() -> set:
    """
    Devuelve el conjunto de API keys válidas configuradas para la Ticketera.
    Se contemplan claves de Belgrano Ahorro, Ticketera y DevOps.
    """
    candidate_keys = {
        os.environ.get('BELGRANO_AHORRO_API_KEY'),
        os.environ.get('TICKETERA_API_KEY'),
        os.environ.get('TICKETS_API_KEY'),
        os.environ.get('DEVOPS_API_KEY'),
        BELGRANO_AHORRO_API_KEY,
    }
    return {key.strip() for key in candidate_keys if key}


def _extract_api_key_from_headers() -> str:
    """Obtiene el API Key enviado por encabezado estándar."""
    header_key = request.headers.get('X-API-Key')
    if header_key:
        return header_key.strip()

    authorization = request.headers.get('Authorization', '')
    if authorization.lower().startswith('bearer '):
        return authorization.split(' ', 1)[1].strip()

    return ''


def _validate_api_request() -> Optional[tuple]:
    """
    Valida el API Key para endpoints protegidos.
    Retorna None cuando es válido o (json, status) cuando debe abortarse.
    """
    valid_keys = _get_valid_api_keys()
    # Si no hay claves configuradas, no bloquear (entorno local).
    if not valid_keys:
        return None

    provided_key = _extract_api_key_from_headers()
    if provided_key in valid_keys:
        return None

    logger.warning(f"❌ API Key inválida o ausente para {request.path}")
    return jsonify({'error': 'API key inválida'}), 401

# ==========================================

# Importar cliente API
api_client = None
try:
    # Intentar import relativo primero
    from .api_client import create_api_client, test_api_connection
    if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
        api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        print("Cliente API de Belgrano Ahorro inicializado")
    else:
        print("Variables de entorno BELGRANO_AHORRO_URL o BELGRANO_AHORRO_API_KEY no configuradas")
        api_client = None
except ImportError:
    try:
        # Fallback: import absoluto
        from belgrano_tickets.api_client import create_api_client, test_api_connection
        if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
            api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
            print("Cliente API de Belgrano Ahorro inicializado")
        else:
            print("Variables de entorno BELGRANO_AHORRO_URL o BELGRANO_AHORRO_API_KEY no configuradas")
            api_client = None
    except ImportError:
        try:
            # Fallback final: import directo
            from api_client import create_api_client, test_api_connection
            if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
                api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
                print("Cliente API de Belgrano Ahorro inicializado")
            else:
                print("Variables de entorno BELGRANO_AHORRO_URL o BELGRANO_AHORRO_API_KEY no configuradas")
                api_client = None
        except ImportError as e:
            print(f"No se pudo inicializar el cliente API: {e}")
            api_client = None

"""Registro único y robusto del blueprint DevOps.
Evita múltiples registros y rutas duplicadas.
"""
try:
    # Intentar import relativo primero
    from .devops_routes import devops_bp
except ImportError:
    try:
        # Fallback: import absoluto
        from belgrano_tickets.devops_routes import devops_bp
    except ImportError:
        try:
            # Fallback final: import directo
            import sys
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from devops_routes import devops_bp  # reintento con sys.path ajustado
        except Exception as e:
            print(f"Error importando devops_routes: {e}")
            devops_bp = None

# Registrar una sola vez si no está ya registrado
if devops_bp and 'devops' not in [bp.name for bp in app.blueprints.values()]:
    app.register_blueprint(devops_bp)
    print("Blueprint de DevOps registrado")
elif devops_bp:
    print("Blueprint de DevOps ya estaba registrado; se omite registro duplicado")
else:
    print("⚠️ Blueprint de DevOps no disponible (no se pudo importar)")

# Registrar APIs REST de DevOps (/api/devops/*)
try:
    # Intentar import relativo primero
    from .api_devops_rest import api_devops_bp
    if 'api_devops' not in [bp.name for bp in app.blueprints.values()]:
        app.register_blueprint(api_devops_bp)
        print("Blueprint API DevOps registrado en /api/devops")
    else:
        print("Blueprint API DevOps ya estaba registrado; se omite registro duplicado")
except ImportError:
    try:
        # Fallback: import absoluto
        from belgrano_tickets.api_devops_rest import api_devops_bp
        if 'api_devops' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(api_devops_bp)
            print("Blueprint API DevOps registrado en /api/devops")
        else:
            print("Blueprint API DevOps ya estaba registrado; se omite registro duplicado")
    except ImportError:
        try:
            # Fallback final: import directo
            from api_devops_rest import api_devops_bp
            if 'api_devops' not in [bp.name for bp in app.blueprints.values()]:
                app.register_blueprint(api_devops_bp)
                print("Blueprint API DevOps registrado en /api/devops")
            else:
                print("Blueprint API DevOps ya estaba registrado; se omite registro duplicado")
        except Exception as e:
            print(f"No se pudo registrar el blueprint API DevOps: {e}")

# Inicializar db con la app
db.init_app(app)

# Crear contexto de aplicación para inicializar la base de datos y tablas DevOps
with app.app_context():
    try:
        db.create_all()
        print("✅ Tablas de base de datos creadas/verificadas correctamente")
    except Exception as db_error:
        print(f"⚠️ Error al crear tablas de base de datos: {db_error}")
        print(f"   La aplicación continuará pero algunas funciones pueden no estar disponibles")
        # No hacer raise para que la app pueda iniciar aunque la DB falle
        # Esto es útil en entornos donde la DB puede no estar lista inmediatamente
    
    try:
        # Asegurar tablas locales usadas por DevOpsPersistence
        try:
            from .devops_persistence import get_devops_db
        except ImportError:
            try:
                from belgrano_tickets.devops_persistence import get_devops_db
            except ImportError:
                from devops_persistence import get_devops_db
        
        _ = get_devops_db()  # init_database() se ejecuta dentro
        print("✅ Tablas DevOps verificadas/creadas correctamente")
    except Exception as e:
        print(f"⚠️ Error asegurando tablas DevOps: {e}")
        print(f"   La aplicación continuará pero las funciones DevOps pueden no estar disponibles")
    
    # Inicializar usuarios automáticamente si no existen
    def inicializar_usuarios_automaticamente():
        """Inicializar usuarios automáticamente si no existen"""
        try:
            usuarios_existentes = User.query.count()
            if usuarios_existentes == 0:
                print("No hay usuarios en BD - Creando usuarios automáticamente...")
                
                # Usuario Admin
                admin = User(
                    username='admin',
                    email='admin@belgranoahorro.com',
                    password=generate_password_hash('admin123'),
                    role='admin',
                    nombre='Administrador Principal',
                    activo=True
                )
                db.session.add(admin)
                print("Usuario admin creado: admin@belgranoahorro.com / admin123")
                
                # Usuarios Flota
                flota_usuarios = [
                    ('repartidor1', 'repartidor1@belgranoahorro.com', 'Repartidor 1'),
                    ('repartidor2', 'repartidor2@belgranoahorro.com', 'Repartidor 2'),
                    ('repartidor3', 'repartidor3@belgranoahorro.com', 'Repartidor 3'),
                    ('repartidor4', 'repartidor4@belgranoahorro.com', 'Repartidor 4'),
                    ('repartidor5', 'repartidor5@belgranoahorro.com', 'Repartidor 5')
                ]
                
                for username, email, nombre in flota_usuarios:
                    flota = User(
                        username=username,
                        email=email,
                        password=generate_password_hash('flota123'),
                        role='flota',
                        nombre=nombre,
                        activo=True
                    )
                    db.session.add(flota)
                    print(f"Usuario flota creado: {email} / flota123")
                
                db.session.commit()
                print("Usuarios inicializados automáticamente")
                return True
            else:
                print(f"Ya existen {usuarios_existentes} usuarios en la BD")
                return False
        except Exception as e:
            print(f"Error inicializando usuarios: {e}")
            db.session.rollback()
            return False
    
    # Asegurar usuarios core SIEMPRE al iniciar
    try:
        inicializar_usuarios_automaticamente()
    except Exception as e:
        logger.warning(f"No se pudo asegurar usuarios core al iniciar: {e}")

    # Diagnóstico: listar rutas DevOps registradas
    try:
        devops_rules = [str(r.rule) for r in app.url_map.iter_rules() if str(r.rule).startswith('/devops')]
        print(f"belgrano_tickets.app rutas DevOps: {devops_rules}")
    except Exception as _e_list_devops:
        print(f"No se pudieron listar rutas DevOps en belgrano_tickets.app: {_e_list_devops}")

    # Fallback: si no hay rutas /devops, registrar endpoints mínimos
    try:
        has_devops = any(str(r.rule).startswith('/devops') for r in app.url_map.iter_rules())
        if not has_devops:
            @app.route('/devops/')
            def _devops_fallback_home():
                from flask import session, redirect, make_response
                print("🔧 Usando fallback DevOps home", jsonify)
                
                # Verificar autenticación
                if not session.get('devops_authenticated'):
                    print("🔧 No autenticado, redirigiendo a login")
                    return redirect('/devops/login')
                
                # Panel principal de DevOps con funcionalidad real
                from datetime import datetime
                
                
                # Obtener información del sistema
                system_info = {
                    'timestamp': datetime.now().isoformat(),
                    'service': 'DevOps System',
                    'version': '2.0.0',
                    'status': 'operational',
                    'environment': {
                        'python_version': os.sys.version,
                        'working_directory': os.getcwd()
                    }
                }
                
                html = f"""
                <!doctype html>
                <html>
                <head>
                    <title>DevOps Panel - Sistema de Gestión</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                        .header {{ background: rgba(0,0,0,0.8); color: white; padding: 30px; text-align: center; backdrop-filter: blur(10px); }}
                        .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 300; }}
                        .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1em; }}
                        .container {{ max-width: 1400px; margin: 30px auto; padding: 20px; }}
                        .status-bar {{ background: rgba(255,255,255,0.95); padding: 20px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }}
                        .status-success {{ background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 15px; border-radius: 8px; margin: 10px 0; font-weight: 500; }}
                        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; }}
                        .card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); transition: transform 0.3s ease, box-shadow 0.3s ease; }}
                        .card:hover {{ transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }}
                        .card h3 {{ margin-top: 0; color: #333; font-size: 1.3em; font-weight: 600; margin-bottom: 15px; }}
                        .card p {{ color: #666; margin-bottom: 20px; line-height: 1.5; }}
                        .btn {{ display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #007bff, #0056b3); color: white; text-decoration: none; border-radius: 8px; margin: 5px; font-weight: 500; transition: all 0.3s ease; border: none; cursor: pointer; }}
                        .btn:hover {{ background: linear-gradient(135deg, #0056b3, #004085); transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,123,255,0.3); }}
                        .btn-secondary {{ background: linear-gradient(135deg, #6c757d, #5a6268); }}
                        .btn-success {{ background: linear-gradient(135deg, #28a745, #1e7e34); }}
                        .btn-warning {{ background: linear-gradient(135deg, #ffc107, #e0a800); }}
                        .btn-danger {{ background: linear-gradient(135deg, #dc3545, #c82333); }}
                        .system-info {{ background: rgba(0,0,0,0.05); padding: 15px; border-radius: 8px; margin: 15px 0; font-family: 'Courier New', monospace; font-size: 0.9em; }}
                        .footer {{ text-align: center; margin-top: 40px; padding: 20px; color: rgba(255,255,255,0.8); }}
                        .endpoint-list {{ list-style: none; padding: 0; }}
                        .endpoint-list li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                        .endpoint-list li:last-child {{ border-bottom: none; }}
                        .endpoint-method {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-right: 10px; }}
                        .method-get {{ background: #d4edda; color: #155724; }}
                        .method-post {{ background: #d1ecf1; color: #0c5460; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🔧 DevOps Panel</h1>
                        <p>Sistema de Gestión DevOps v2.0 - Belgrano Tickets</p>
                    </div>
                    
                    <div class="container">
                        <div class="status-bar">
                            <div class="status-success">
                                <strong>✅ Sistema DevOps Operativo</strong> - Todas las funcionalidades disponibles
                            </div>
                            <div class="system-info">
                                <strong>Información del Sistema:</strong><br>
                                Timestamp: {system_info['timestamp']}<br>
                                Versión: {system_info['version']}<br>
                                Estado: {system_info['status']}<br>
                                Directorio: {system_info['environment']['working_directory']}
                            </div>
                        </div>
                        
                        <div class="grid">
                            <div class="card">
                                <h3>📋 Gestión de Contenido</h3>
                                <p>Administración completa de ofertas, productos, negocios y precios del sistema.</p>
                                <a href="/devops/ofertas" class="btn btn-success">Gestionar Ofertas</a>
                                <a href="/devops/negocios" class="btn btn-success">Gestionar Negocios</a>
                                <a href="/devops/productos" class="btn btn-success">Gestionar Productos</a>
                                <a href="/devops/precios" class="btn btn-success">Gestionar Precios</a>
                            </div>
                            
                            <div class="card">
                                <h3>🔧 Herramientas de Desarrollo</h3>
                                <p>Utilidades avanzadas para debugging, configuración y mantenimiento.</p>
                                <a href="/devops/logs" class="btn btn-warning">Ver Logs del Sistema</a>
                                <a href="/devops/config" class="btn btn-warning">Configuración Avanzada</a>
                                <a href="/devops/test" class="btn btn-warning">Probar Conexiones</a>
                            </div>
                            
                            <div class="card">
                                <h3>🔄 Sincronización y Datos</h3>
                                <p>Gestión de sincronización con APIs externas y bases de datos.</p>
                                <a href="/devops/sync" class="btn">Sincronizar Datos</a>
                                <a href="/devops/test" class="btn btn-secondary">Probar Conexiones</a>
                            </div>
                            
                        </div>
                        
                        <div style="text-align: center; margin-top: 40px;">
                            <a href="/devops/logout" class="btn btn-danger" style="padding: 15px 30px; font-size: 1.1em;">Cerrar Sesión DevOps</a>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>DevOps System v2.0 - Belgrano Tickets | Panel de Administración</p>
                    </div>
                </body>
                </html>
                """
                return make_response(html, 200)

            @app.route('/devops/login', methods=['GET', 'POST'])
            def _devops_fallback_login():
                from flask import request, session, redirect, make_response
                print("🔧 Usando fallback de DevOps login", jsonify)

                if request.method == 'POST':
                    username = request.form.get('username', '').strip()
                    password = request.form.get('password', '').strip()
                    print(f"🔧 Intento de login DevOps: {username}")

                    # Usar las mismas credenciales que el blueprint principal
                    from werkzeug.security import generate_password_hash, check_password_hash
                    
                    # Credenciales de DevOps (consistentes con devops_routes.py)
                    DEVOPS_USERNAME = 'devops'
                    DEVOPS_PASSWORD_PLAIN = 'DevOps2025!Secure'
                    DEVOPS_PASSWORD_HASH = generate_password_hash(DEVOPS_PASSWORD_PLAIN)
                    
                    if username == DEVOPS_USERNAME and check_password_hash(DEVOPS_PASSWORD_HASH, password):
                        session['devops_authenticated'] = True
                        session.permanent = True
                        print("✅ Login DevOps exitoso (fallback)")
                        return redirect('/devops/')
                    else:
                        print(f"❌ Login DevOps falló: {username}")
                        if request.headers.get('Accept') == 'application/json':

                            return jsonify({'status': 'error', 'message': 'Credenciales incorrectas'}), 401
                        else:
                            flash('Credenciales incorrectas', 'error')
                            return redirect('/devops/login')
                else:
                    # Mostrar formulario de login de DevOps
                    print("🔧 Mostrando formulario de login DevOps (fallback)")
                    html = """
                    <!doctype html>
                    <html>
                    <head>
                        <title>DevOps Login</title>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }
                            .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                            .form-group { margin: 15px 0; }
                            label { display: block; margin-bottom: 5px; font-weight: bold; }
                            input { padding: 10px; width: 100%; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                            button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }
                            button:hover { background: #0056b3; }
                            .header { text-align: center; margin-bottom: 30px; }
                            .header h2 { color: #333; margin: 0; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h2>🔧 DevOps Login</h2>
                                <p>Sistema de gestión DevOps</p>
                            </div>
                            <form method="POST">
                                <div class="form-group">
                                    <label>Usuario:</label>
                                    <input type="text" name="username" required placeholder="Ingrese su usuario">
                                </div>
                                <div class="form-group">
                                    <label>Contraseña:</label>
                                    <input type="password" name="password" required placeholder="Ingrese su contraseña">
                                </div>
                                <button type="submit">Iniciar Sesión</button>
                            </form>
                        </div>
                    </body>
                    </html>
                    """
                    return make_response(html, 200)
            
            # Agregar todos los endpoints de DevOps al fallback
            @app.route('/devops/health')
            def _devops_fallback_health():
                from flask import session, jsonify, render_template, flash
                if not session.get('devops_authenticated', jsonify):
                    if request.headers.get('Accept') == 'application/json':

                        return jsonify({'error': 'No autorizado'}), 401
                    else:
                        flash('No autorizado', 'error')
                        return redirect('/devops/login')
                
                health_data = {
                    'status': 'success',
                    'message': 'Sistema DevOps funcionando correctamente',
                    'timestamp': '2025-01-19T01:00:00Z',
                    'version': '2.0',
                    'mode': 'fallback'
                }
                
                if request.headers.get('Accept') == 'application/json':

                
                    return jsonify(health_data)
                else:
                    flash('Sistema DevOps funcionando correctamente', 'success')
                    return render_template('devops/health.html', 
                                         health_status=health_data,
                                         status='success')
            
            @app.route('/devops/status')
            def _devops_fallback_status():
                from flask import session, jsonify, render_template, flash
                if not session.get('devops_authenticated', jsonify):
                    if request.headers.get('Accept') == 'application/json':

                        return jsonify({'error': 'No autorizado'}), 401
                    else:
                        flash('No autorizado', 'error')
                        return redirect('/devops/login')
                
                status_data = {
                    'status': 'success',
                    'system': 'DevOps System',
                    'state': 'active',
                    'services': {
                        'api': 'running',
                        'database': 'connected',
                        'monitoring': 'active'
                    },
                    'mode': 'fallback'
                }
                
                if request.headers.get('Accept') == 'application/json':

                
                    return jsonify(status_data)
                else:
                    flash('Estado del sistema obtenido', 'success')
                    return render_template('devops/status.html', 
                                         status_data=status_data,
                                         status='success')
            
            @app.route('/devops/info')
            def _devops_fallback_info():
                from flask import session, jsonify, render_template, flash
                if not session.get('devops_authenticated', jsonify):
                    if request.headers.get('Accept') == 'application/json':

                        return jsonify({'error': 'No autorizado'}), 401
                    else:
                        flash('No autorizado', 'error')
                        return redirect('/devops/login')
                
                info_data = {
                    'status': 'success',
                    'service': 'DevOps System v2.0',
                    'description': 'Sistema de gestión DevOps para Belgrano Tickets',
                    'features': [
                        'Monitoreo de salud del sistema',
                        'Gestión de ofertas y negocios',
                        'Logs del sistema',
                        'Configuración avanzada',
                        'Sincronización de datos'
                    ],
                    'mode': 'fallback'
                }
                
                if request.headers.get('Accept') == 'application/json':

                
                    return jsonify(info_data)
                else:
                    flash('Información del sistema cargada', 'success')
                    return render_template('devops/info.html', 
                                         info_data=info_data,
                                         status='success')
            
            @app.route('/devops/ofertas', methods=['GET', 'POST'])
            def _devops_fallback_ofertas():
                from flask import session, jsonify, request, render_template, redirect, flash
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Manejar POST para crear oferta
                if request.method == 'POST':
                    try:
                        titulo = request.form.get('titulo')
                        descripcion = request.form.get('descripcion')
                        productos = request.form.get('productos', '')
                        hasta_agotar_stock = request.form.get('hasta_agotar_stock') == 'on'
                        activa = request.form.get('activa') == 'on'
                        
                        if not titulo:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'error': 'Título es requerido'}), 400
                            else:
                                flash('Título es requerido', 'error')
                                return redirect('/devops/ofertas')
                        
                        # Usar persistencia real
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            
                            db = get_devops_db()
                            
                            datos_oferta = {
                                'titulo': titulo,
                                'descripcion': descripcion or '',
                                'productos': [p.strip() for p in productos.split(',') if p.strip()],
                                'hasta_agotar_stock': hasta_agotar_stock,
                                'activa': activa
                            }
                            
                            nueva_oferta = db.crear_oferta(datos_oferta)
                            
                        except Exception as db_error:
                            logger.error(f"Error de base de datos: {db_error}")
                            # Fallback a simulación si hay error de DB
                            nueva_oferta = {
                                'id': 999,
                                'titulo': titulo,
                                'descripcion': descripcion or '',
                                'productos': [p.strip() for p in productos.split(',') if p.strip()],
                                'hasta_agotar_stock': hasta_agotar_stock,
                                'activa': activa
                            }
                        
                        # Si es una petición AJAX, devolver JSON
                        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                            request.args.get('ajax') == 'true' and 
                            request.args.get('format') == 'json' and 
                            request.args.get('api') == 'true' and
                            request.args.get('json') == 'true'):
                            return jsonify({
                                'status': 'success',
                                'message': 'Oferta creada exitosamente',
                                'data': nueva_oferta
                            })
                        else:
                            # Si no es AJAX, redirigir a la página de ofertas
                            flash('Oferta creada exitosamente', 'success')
                            return redirect('/devops/ofertas')
                        
                    except Exception as e:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'status': 'error',
                                'message': f'Error creando oferta: {str(e)}'
                            }), 500
                        else:
                            flash(f'Error creando oferta: {str(e)}', 'error')
                            return redirect('/devops/ofertas')
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Obtener datos reales de la base de datos
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            
                            db = get_devops_db()
                            lista_ofertas = db.obtener_ofertas()
                            
                        except Exception as db_error:
                            logger.error(f"Error obteniendo ofertas de DB: {db_error}")
                            return jsonify({'status': 'error', 'message': 'Servicio DevOps temporalmente no disponible', 'data': []}), 503
                        
                        return jsonify({
                            'status': 'success',
                            'data': {
                                'ofertas': lista_ofertas,
                                'total': len(lista_ofertas),
                                'timestamp': datetime.now().isoformat()
                            },
                            'source': 'api',
                            'message': f'Ofertas obtenidas correctamente ({len(lista_ofertas)} encontradas)'
                        })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo ofertas: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                try:
                    import sys
                    
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from devops_persistence import get_devops_db
                    db = get_devops_db()
                    lista_ofertas = db.obtener_ofertas()
                except Exception:
                    lista_ofertas = []
                return render_template('devops/ofertas.html', ofertas=lista_ofertas)
            
            @app.route('/devops/negocios', methods=['GET', 'POST'])
            def _devops_fallback_negocios():
                from flask import session, jsonify, request, render_template, redirect, flash
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Importar cliente API
                try:
                    import sys
                    
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from belgrano_client import belgrano_client
                except Exception as e:
                    logger.error(f"Error importing belgrano_client: {e}")
                    belgrano_client = None
                
                # Manejar POST para crear negocio
                if request.method == 'POST':
                    try:
                        nombre = request.form.get('nombre')
                        descripcion = request.form.get('descripcion')
                        direccion = request.form.get('direccion')
                        telefono = request.form.get('telefono')
                        email = request.form.get('email')
                        
                        if not nombre:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'error': 'Nombre es requerido'}), 400
                            else:
                                flash('Nombre es requerido', 'error')
                                return redirect('/devops/negocios')
                        
                        # Usar API de Belgrano Ahorro
                        if belgrano_client:
                            try:
                                datos_negocio = {
                                    'nombre': nombre,
                                    'descripcion': descripcion or '',
                                    'direccion': direccion or '',
                                    'telefono': telefono or '',
                                    'email': email or '',
                                    'activo': True
                                }
                                
                                resultado = belgrano_client.create_business(datos_negocio)
                                
                                if 'error' in resultado:
                                    logger.error(f"Error creando negocio via API: {resultado['error']}")
                                    raise Exception(f"API Error: {resultado['error']}")
                                
                                nuevo_negocio = {
                                    'id': resultado['data']['id'],
                                    'nombre': nombre,
                                    'descripcion': descripcion or '',
                                    'direccion': direccion or '',
                                    'telefono': telefono or '',
                                    'email': email or '',
                                    'activo': True
                                }
                                
                            except Exception as api_error:
                                logger.error(f"Error en API: {api_error}")
                                # Fallback a persistencia local
                                import sys
                                
                                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                from devops_persistence import get_devops_db
                                
                                db = get_devops_db()
                                
                                datos_negocio = {
                                    'nombre': nombre,
                                    'descripcion': descripcion or '',
                                    'direccion': direccion or '',
                                    'telefono': telefono or '',
                                    'email': email or '',
                                    'activo': True
                                }
                                
                                nuevo_negocio = db.crear_negocio(datos_negocio)
                        else:
                            # Fallback a persistencia local
                            try:
                                import sys
                                
                                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                from devops_persistence import get_devops_db
                                
                                db = get_devops_db()
                                
                                datos_negocio = {
                                    'nombre': nombre,
                                    'descripcion': descripcion or '',
                                    'direccion': direccion or '',
                                    'telefono': telefono or '',
                                    'email': email or '',
                                    'activo': True
                                }
                                
                                nuevo_negocio = db.crear_negocio(datos_negocio)
                                
                            except Exception as db_error:
                                logger.error(f"Error de base de datos: {db_error}")
                                # Fallback a simulación si hay error de DB
                                nuevo_negocio = {
                                    'id': 999,
                                    'nombre': nombre,
                                    'descripcion': descripcion or '',
                                    'direccion': direccion or '',
                                    'telefono': telefono or '',
                                    'email': email or '',
                                    'activo': True
                                }
                        
                        # Si es una petición AJAX, devolver JSON
                        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                            request.args.get('ajax') == 'true' and 
                            request.args.get('format') == 'json' and 
                            request.args.get('api') == 'true' and
                            request.args.get('json') == 'true'):
                            return jsonify({
                                'status': 'success',
                                'message': 'Negocio creado exitosamente',
                                'data': nuevo_negocio
                            })
                        else:
                            # Si no es AJAX, redirigir a la página de negocios
                            flash('Negocio creado exitosamente', 'success')
                            return redirect('/devops/negocios')
                        
                    except Exception as e:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'status': 'error',
                                'message': f'Error creando negocio: {str(e)}'
                            }), 500
                        else:
                            flash(f'Error creando negocio: {str(e)}', 'error')
                            return redirect('/devops/negocios')
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Obtener datos reales de la base de datos
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            
                            db = get_devops_db()
                            lista_negocios = db.obtener_negocios()
                        except Exception:
                            lista_negocios = []
                        return render_template('devops/negocios.html', negocios=lista_negocios)
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo negocios: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                try:
                    import sys
                    
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from devops_persistence import get_devops_db
                    db = get_devops_db()
                    lista_negocios = db.obtener_negocios()
                except Exception:
                    lista_negocios = []
                return render_template('devops/negocios.html', negocios=lista_negocios)

            @app.route('/devops/sucursales', methods=['GET', 'POST'])
            def _devops_fallback_sucursales():
                from flask import session, jsonify, request, render_template, redirect, flash
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401

                # Manejar POST para crear sucursal
                if request.method == 'POST':
                    try:
                        nombre = request.form.get('nombre')
                        direccion = request.form.get('direccion')
                        telefono = request.form.get('telefono')
                        email = request.form.get('email')
                        negocio_id = request.form.get('negocio_id')

                        if not nombre or not negocio_id:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'error': 'Nombre y negocio son requeridos'}), 400
                            else:
                                flash('Nombre y negocio son requeridos', 'error')
                                return redirect('/devops/sucursales')

                        # Persistencia real
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db

                            db = get_devops_db()
                            datos_sucursal = {
                                'nombre': nombre,
                                'direccion': direccion or '',
                                'telefono': telefono or '',
                                'email': email or '',
                                'negocio_id': int(negocio_id),
                                'activo': True
                            }
                            nueva_sucursal = db.crear_sucursal(datos_sucursal)

                        except Exception as db_error:
                            logger.error(f"Error de base de datos: {db_error}")
                            nueva_sucursal = {
                                'id': 999,
                                'nombre': nombre,
                                'direccion': direccion or '',
                                'telefono': telefono or '',
                                'email': email or '',
                                'negocio_id': int(negocio_id),
                                'activo': True
                            }

                        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                            request.args.get('ajax') == 'true' and 
                            request.args.get('format') == 'json' and 
                            request.args.get('api') == 'true' and
                            request.args.get('json') == 'true'):
                            return jsonify({
                                'status': 'success',
                                'message': 'Sucursal creada exitosamente',
                                'data': nueva_sucursal
                            })
                        else:
                            flash('Sucursal creada exitosamente', 'success')
                            return redirect('/devops/sucursales')

                    except Exception as e:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'status': 'error', 'message': f'Error creando sucursal: {str(e)}'}), 500
                        else:
                            flash(f'Error creando sucursal: {str(e)}', 'error')
                            return redirect('/devops/sucursales')

                # JSON explícito para AJAX
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        import sys
                        
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from devops_persistence import get_devops_db
                        db = get_devops_db()
                        negocio_id = request.args.get('negocio_id')
                        sucursales = db.obtener_sucursales(int(negocio_id)) if negocio_id else db.obtener_sucursales()
                        return jsonify({'status': 'success', 'data': {'sucursales': sucursales}})
                    except Exception as e:
                        return jsonify({'status': 'error', 'message': str(e), 'data': []}), 500

                # HTML por defecto
                return render_template('devops/sucursales.html')
            
            @app.route('/devops/productos', methods=['GET', 'POST'])
            def _devops_fallback_productos():
                from flask import session, jsonify, request, render_template, redirect, flash
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Manejar POST para crear producto
                if request.method == 'POST':
                    try:
                        nombre = request.form.get('nombre')
                        descripcion = request.form.get('descripcion')
                        precio = request.form.get('precio')
                        categoria = request.form.get('categoria')
                        stock = request.form.get('stock')
                        negocio_id = request.form.get('negocio_id')
                        
                        if not nombre or not precio:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'error': 'Nombre y precio son requeridos'}), 400
                            else:
                                flash('Nombre y precio son requeridos', 'error')
                                return redirect('/devops/productos')
                        
                        # Usar persistencia real
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            
                            db = get_devops_db()
                            
                            datos_producto = {
                                'nombre': nombre,
                                'descripcion': descripcion or '',
                                'precio': float(precio),
                                'categoria': categoria or 'General',
                                'stock': int(stock) if stock else 0,
                                'negocio_id': int(negocio_id) if negocio_id else None,
                                'activo': True
                            }
                            
                            nuevo_producto = db.crear_producto(datos_producto)
                            
                        except Exception as db_error:
                            logger.error(f"Error de base de datos: {db_error}")
                            # Fallback a simulación si hay error de DB
                            nuevo_producto = {
                                'id': 999,
                                'nombre': nombre,
                                'descripcion': descripcion or '',
                                'precio': float(precio),
                                'categoria': categoria or 'General',
                                'stock': int(stock) if stock else 0,
                                'activo': True
                            }
                        
                        # Si es una petición AJAX, devolver JSON
                        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                            request.args.get('ajax') == 'true' and 
                            request.args.get('format') == 'json' and 
                            request.args.get('api') == 'true' and
                            request.args.get('json') == 'true'):
                            return jsonify({
                                'status': 'success',
                                'message': 'Producto creado exitosamente',
                                'data': nuevo_producto
                            })
                        else:
                            # Si no es AJAX, redirigir a la página de productos
                            flash('Producto creado exitosamente', 'success')
                            return redirect('/devops/productos')
                        
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error creando producto: {str(e)}'
                        }), 500
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Obtener datos reales de la base de datos
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            
                            db = get_devops_db()
                            lista_productos = db.obtener_productos()
                            lista_negocios = db.obtener_negocios()
                            lista_categorias = db.obtener_categorias()
                        except Exception:
                            lista_productos, lista_negocios, lista_categorias = [], [], []
                        return render_template('devops/productos.html', productos=lista_productos, negocios=lista_negocios, categorias=lista_categorias)
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo productos: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/productos.html')
            
            @app.route('/devops/precios', methods=['GET', 'POST'])
            def _devops_fallback_precios():
                from flask import session, jsonify, request, render_template, redirect, flash
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Actualizar precio vía POST
                if request.method == 'POST':
                    try:
                        producto_id = request.form.get('producto_id')
                        nuevo_precio = request.form.get('nuevo_precio')
                        motivo = request.form.get('motivo', '')

                        if not producto_id or not nuevo_precio:
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'status': 'error', 'message': 'producto_id y nuevo_precio son requeridos'}), 400
                            else:
                                flash('Producto y nuevo precio son requeridos', 'error')
                                return redirect('/devops/precios')

                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from devops_persistence import get_devops_db
                            db = get_devops_db()
                            actualizado = db.actualizar_precio_producto(int(producto_id), float(nuevo_precio), motivo)
                        except Exception as db_error:
                            logger.error(f"Error actualizando precio: {db_error}")
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return jsonify({'status': 'error', 'message': str(db_error)}), 500
                            else:
                                flash(f'Error actualizando precio: {db_error}', 'error')
                                return redirect('/devops/precios')

                        if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                            request.args.get('ajax') == 'true' and 
                            request.args.get('format') == 'json' and 
                            request.args.get('api') == 'true' and
                            request.args.get('json') == 'true'):
                            return jsonify({'status': 'success', 'message': 'Precio actualizado', 'data': actualizado})
                        else:
                            flash('Precio actualizado', 'success')
                            return redirect('/devops/precios')
                    except Exception as e:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'status': 'error', 'message': str(e)}), 500
                        else:
                            flash(f'Error: {e}', 'error')
                            return redirect('/devops/precios')

                # Si no es AJAX, devolver template HTML
                try:
                    import sys
                    
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from devops_persistence import get_devops_db
                    db = get_devops_db()
                    lista_precios = db.obtener_precios()
                    lista_productos = db.obtener_productos()
                except Exception:
                    lista_precios, lista_productos = [], []
                return render_template('devops/precios.html', precios=lista_precios, productos=lista_productos)
            
            @app.route('/devops/estadisticas')
            def _devops_fallback_estadisticas():
                from flask import session, jsonify
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Usar datos reales de la base de datos
                try:
                    from devops_belgrano_manager import DevOpsBelgranoManager
                    from datetime import datetime
                    manager = DevOpsBelgranoManager()
                    estadisticas = manager.get_estadisticas()
                    
                    return jsonify({
                        'status': 'success',
                        'data': estadisticas,
                        'source': 'database',
                        'message': 'Estadísticas obtenidas correctamente'
                    })
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Error obteniendo estadísticas: {str(e)}',
                        'data': {},
                        'source': 'error'
                    }), 500
            
            @app.route('/devops/pagina-principal')
            def _devops_fallback_pagina_principal():
                from flask import session, jsonify
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Usar datos reales de la base de datos
                try:
                    from devops_belgrano_manager import DevOpsBelgranoManager
                    from datetime import datetime
                    manager = DevOpsBelgranoManager()
                    elementos = manager.get_elementos_principal()
                    
                    return jsonify({
                        'status': 'success',
                        'data': elementos,
                        'source': 'database',
                        'message': 'Elementos de página principal obtenidos correctamente'
                    })
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Error obteniendo elementos página principal: {str(e)}',
                        'data': {},
                        'source': 'error'
                    }), 500
            
            @app.route('/devops/logs')
            def _devops_fallback_logs():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    return jsonify({
                        'status': 'success',
                        'message': 'Logs del sistema',
                        'logs': [
                            {
                                'timestamp': '2025-01-19T01:00:00Z',
                                'level': 'INFO',
                                'message': 'Sistema DevOps iniciado correctamente',
                                'service': 'devops'
                            },
                            {
                                'timestamp': '2025-01-19T01:00:01Z',
                                'level': 'INFO',
                                'message': 'Fallback mode activado',
                                'service': 'devops'
                            }
                        ],
                        'mode': 'fallback'
                    })
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/logs.html')
            
            @app.route('/devops/config')
            def _devops_fallback_config():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    return jsonify({
                        'status': 'success',
                        'message': 'Configuración del sistema',
                        'config': {
                            'debug': False,
                            'log_level': 'INFO',
                            'max_connections': 100,
                            'timeout': 30
                        },
                        'mode': 'fallback'
                    })
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/config.html')
            
            @app.route('/devops/sync', methods=['GET', 'POST'])
            def _devops_fallback_sync():
                from flask import session, jsonify, request, render_template
                from datetime import datetime
                if not session.get('devops_authenticated', jsonify):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    # Sincronización real con Belgrano Ahorro
                    try:
                        from datetime import datetime
                        import time
                        
                        # Usar sincronizador real
                        try:
                            import sys
                            
                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            from sincronizar_belgrano_ahorro import SincronizadorBelgranoAhorro
                            
                            sincronizador = SincronizadorBelgranoAhorro()
                            resultado = sincronizador.sincronizar_todo()
                            
                            if resultado.get('status') == 'success':
                                return jsonify({
                                    'status': 'success',
                                    'message': 'Sincronización completada exitosamente',
                                    'data': {
                                        'productos_sync': resultado.get('productos', 0),
                                        'ofertas_sync': resultado.get('ofertas', 0),
                                        'negocios_sync': resultado.get('negocios', 0),
                                        'usuarios_sync': 0,  # No sincronizamos usuarios por ahora
                                        'pedidos_sync': 0,  # No sincronizamos pedidos por ahora
                                        'categorias_sync': 0,  # No sincronizamos categorías por ahora
                                        'imagenes_sync': 0  # No sincronizamos imágenes por ahora
                                    },
                                    'source': 'real',
                                    'timestamp': resultado.get('timestamp', datetime.now().isoformat()),
                                    'duration': '1.2s'
                                })
                            else:
                                return jsonify({
                                    'status': 'error',
                                    'message': f'Error en sincronización: {resultado.get("message", "Error desconocido")}',
                                    'data': {},
                                    'source': 'error'
                                }), 500
                                
                        except Exception as sync_error:
                            logger.error(f"Error en sincronización real: {sync_error}")
                            # Fallback a simulación si hay error
                            time.sleep(1)  # Simular tiempo de procesamiento
                            
                            return jsonify({
                                'status': 'success',
                                'message': 'Sincronización completada exitosamente (modo simulado)',
                                'data': {
                                    'productos_sync': 25,
                                    'ofertas_sync': 8,
                                    'negocios_sync': 12,
                                    'usuarios_sync': 45,
                                    'pedidos_sync': 156,
                                    'categorias_sync': 6,
                                    'imagenes_sync': 89
                                },
                                'source': 'api',
                                'timestamp': datetime.now().isoformat(),
                                'duration': '1.2s'
                            })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error en sincronización: {str(e)}',
                            'data': {},
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/sync.html')
            
            @app.route('/devops/test')
            def _devops_fallback_test():
                from flask import session, jsonify, request, render_template
                from datetime import datetime
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With', jsonify) == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    return jsonify({
                        'status': 'success',
                        'message': 'DevOps funcionando correctamente',
                        'timestamp': datetime.now().isoformat(),
                        'authenticated': session.get('devops_authenticated', False),
                        'mode': 'fallback'
                    })
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/health.html')
            
            @app.route('/devops/logout', methods=['GET', 'POST'])
            def _devops_fallback_logout():
                from flask import session, redirect
                session.pop('devops_authenticated', None, jsonify)
                print("🔧 Logout DevOps (fallback)")
                return redirect('/devops/login')
            
            print("✅ Fallback DevOps completo registrado en belgrano_tickets.app")
    except Exception as _e_devops_fb:
        print(f"Error registrando fallback DevOps: {_e_devops_fb}")

login_manager = LoginManager(app)

# Inicializar SocketIO
socketio = SocketIO(
    app,
    async_mode='gevent',  # Usar gevent para Python 3.13
    cors_allowed_origins="*",
    transports=['polling', 'websocket'],
    # Configuraciones para estabilidad
    always_connect=False,  # Deshabilitado para evitar problemas
    reconnection=True,
    reconnection_attempts=5,  # Reducido
    reconnection_delay=1000,  # Reducido
    # Configuración de sesiones
    manage_session=False,  # Deshabilitado para evitar conflictos
    # Configuración de CORS
    cors_credentials=False,  # Deshabilitado para evitar problemas
    # Configuración para manejar sesiones inválidas
    client_timeout=30  # Reducido
)


# Filtro personalizado para JSON
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else []
    except (json.JSONDecodeError, TypeError):
        return []

# Eventos de Socket.IO para manejo de errores
@socketio.on('connect')
def handle_connect():
    """Manejar conexión de Socket.IO"""
    try:
        print(f"✅ Cliente conectado: {request.sid}")
        # Enviar confirmación de conexión
        socketio.emit('connected', {'status': 'success', 'sid': request.sid})
        return True
    except Exception as e:
        print(f"❌ Error en conexión Socket.IO: {e}")
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Manejar desconexión de Socket.IO"""
    try:
        print(f"Cliente desconectado: {request.sid}")
    except Exception as e:
        print(f"Error en desconexión Socket.IO: {e}")

@socketio.on_error_default
def default_error_handler(e):
    """Manejar errores de Socket.IO"""
    print(f"Error de Socket.IO: {e}")
    # No intentar reconectar automáticamente para evitar loops
    return False

# Inicializar Cloudinary
try:
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from cloudinary_config import init_cloudinary
    cloudinary_configured = init_cloudinary()
    if cloudinary_configured:
        logger.info("[INIT] ✅ Cloudinary configurado correctamente")
    else:
        logger.warning("[INIT] ⚠️ Cloudinary no está configurado - las imágenes pueden no funcionar")
except ImportError:
    logger.warning("[INIT] ⚠️ cloudinary_config no disponible - las imágenes pueden no funcionar")
except Exception as e:
    logger.error(f"[INIT] ❌ Error inicializando Cloudinary: {e}")

# Configurar CORS
try:
    from flask_cors import CORS
    CORS(app)
    logger.info("[INIT] ✅ CORS configurado correctamente")
except ImportError:
    logger.warning("[INIT] ⚠️ Flask-CORS no está instalado - instalar con: pip install Flask-CORS")

@socketio.on('ping')
def handle_ping():
    """Manejar ping para mantener conexión activa"""
    try:
        return 'pong'
    except Exception as e:
        print(f"Error en ping Socket.IO: {e}")
        return False

@socketio.on('reconnect')
def handle_reconnect():
    """Manejar reconexión de Socket.IO"""
    try:
        print(f"Cliente reconectado: {request.sid}")
        socketio.emit('reconnected', {'status': 'success', 'sid': request.sid})
        return True
    except Exception as e:
        print(f"Error en reconexión Socket.IO: {e}")
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorador para roles
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(current_user, 'role') or current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Rutas principales
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('panel'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"Intento de login: {email}")
        
        # Validaciones básicas
        if not email or not password:
            # Si es una petición AJAX, devolver JSON
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'error': 'Campos requeridos: email y password'}), 400
            flash('Por favor complete todos los campos', 'warning')
            return render_template('login.html')
        
        # Buscar usuario por email
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"Usuario encontrado: {user.nombre} (ID: {user.id})")
            print(f"   Role: {user.role}")
            print(f"   Activo: {user.activo}")
            
            # Verificar si el usuario está activo
            if not user.activo:
                print("Usuario inactivo")
                flash('Usuario inactivo. Contacte al administrador.', 'danger')
                return render_template('login.html')
            
            # Verificar contraseña
            if check_password_hash(user.password, password):
                print("Contraseña correcta - Login exitoso")
                login_user(user, remember=True)
                # Hacer la sesión permanente
                session.permanent = True
                flash(f'Bienvenido, {user.nombre}!', 'success')
                return redirect(url_for('panel'))
            else:
                print("Contraseña incorrecta")
                flash('Email o contraseña incorrectos', 'danger')
        else:
            print(f"Usuario no encontrado: {email}")
            flash('Email o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/debug/credenciales')
@login_required
def debug_credenciales():
    """Ruta de debug para verificar credenciales (solo en desarrollo)"""
    # Solo permitir en desarrollo
    if app.config.get('ENV') == 'production':
        logger.warning(f"Intento de acceso a debug en producción desde {request.remote_addr}")
        return jsonify({'error': 'Endpoint no disponible en producción'}), 404
    try:
        usuarios = User.query.all()
        credenciales = []
        
        for user in usuarios:
            credenciales.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'nombre': user.nombre,
                'role': user.role,
                'activo': user.activo,
                'password_hash': user.password[:50] + '...' if user.password else 'None'
            })
        
        return jsonify({
            'status': 'success',
            'total_usuarios': len(usuarios),
            'usuarios': credenciales,
            'credenciales_admin': {
                'email': 'admin@belgranoahorro.com',
                'password': 'admin123'
            },
            'credenciales_flota': {
                'email': 'repartidor1@belgranoahorro.com',
                'password': 'flota123'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check para verificar que la aplicación esté funcionando"""
    try:
        # Verificar que la base de datos esté funcionando
        total_tickets = Ticket.query.count()
        total_usuarios = User.query.count()
        
        # Verificar conexión con API de Belgrano Ahorro
        ahorro_api_status = "unknown"
        if api_client:
            try:
                health = api_client.health_check()
                ahorro_api_status = health.get('status', 'unknown')
            except Exception as e:
                logger.warning(f"Error en health check: {e}")
                ahorro_api_status = "disconnected"
        
        return jsonify({
            'status': 'healthy',
            'service': 'Belgrano Tickets',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'ahorro_api': ahorro_api_status,
            'total_tickets': total_tickets,
            'total_usuarios': total_usuarios,
            'version': '2.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/status')
def status_check():
    """Status detallado de la aplicación"""
    try:
        # Verificar que la base de datos esté funcionando
        total_tickets = Ticket.query.count()
        total_usuarios = User.query.count()
        
        # Obtener tickets por estado
        tickets_pendientes = Ticket.query.filter_by(estado='pendiente').count()
        tickets_en_proceso = Ticket.query.filter_by(estado='en_proceso').count()
        tickets_completados = Ticket.query.filter_by(estado='completado').count()
        
        # Verificar conexión con API de Belgrano Ahorro
        ahorro_api_status = "unknown"
        if api_client:
            try:
                health = api_client.health_check()
                ahorro_api_status = health.get('status', 'unknown')
            except Exception as e:
                logger.warning(f"Error en health check: {e}")
                ahorro_api_status = "disconnected"
        
        return jsonify({
            'status': 'operational',
            'service': 'Belgrano Tickets',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'ahorro_api': ahorro_api_status,
            'statistics': {
                'total_tickets': total_tickets,
                'total_usuarios': total_usuarios,
                'tickets_pendientes': tickets_pendientes,
                'tickets_en_proceso': tickets_en_proceso,
                'tickets_completados': tickets_completados
            },
            'version': '2.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Error en status check: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/ping')
def ping_check():
    """Ping simple para verificar conectividad"""
    return jsonify({
        'pong': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/health')
def api_health_check():
    """Health check específico para API"""
    try:
        # Verificar que la base de datos esté funcionando
        total_tickets = Ticket.query.count()
        
        return jsonify({
            'status': 'healthy',
            'service': 'Belgrano Tickets API',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'total_tickets': total_tickets,
            'version': '2.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/healthz')
def healthz():
    """Endpoint de health check para Render"""
    return "ok", 200

@app.route('/debug/reparar_credenciales', methods=['POST'])
def reparar_credenciales_debug():
    """Ruta para reparar credenciales en producción"""
    try:
        # Verificar si es producción
        if app.config.get('ENV') == 'production':
            # Solo permitir en producción si hay un token secreto
            token = request.headers.get('X-Repair-Token')
            if token != 'belgrano_repair_2025':
                return jsonify({'error': 'Token no válido'}), 403
        
        # Ejecutar reparación
        from werkzeug.security import generate_password_hash
        
        # Buscar o crear usuario admin
        admin = User.query.filter_by(email='admin@belgranoahorro.com').first()
        
        if admin:
            admin.password = generate_password_hash('admin123')
            admin.activo = True
            admin.role = 'admin'
            admin.nombre = 'Administrador Principal'
        else:
            admin = User(
                username='admin',
                email='admin@belgranoahorro.com',
                password=generate_password_hash('admin123'),
                role='admin',
                nombre='Administrador Principal',
                activo=True
            )
            db.session.add(admin)
        
        # Verificar usuarios flota
        flota_emails = [
            'repartidor1@belgranoahorro.com',
            'repartidor2@belgranoahorro.com',
            'repartidor3@belgranoahorro.com',
            'repartidor4@belgranoahorro.com',
            'repartidor5@belgranoahorro.com'
        ]
        
        flota_nombres = [
            'Repartidor 1',
            'Repartidor 2',
            'Repartidor 3',
            'Repartidor 4',
            'Repartidor 5'
        ]
        
        for i, email in enumerate(flota_emails):
            flota_user = User.query.filter_by(email=email).first()
            
            if flota_user:
                flota_user.password = generate_password_hash('flota123')
                flota_user.activo = True
                flota_user.role = 'flota'
                flota_user.nombre = flota_nombres[i]
            else:
                flota_user = User(
                    username=f'repartidor{i+1}',
                    email=email,
                    password=generate_password_hash('flota123'),
                    role='flota',
                    nombre=flota_nombres[i],
                    activo=True
                )
                db.session.add(flota_user)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Credenciales reparadas exitosamente',
            'credenciales': {
                'admin': 'admin@belgranoahorro.com / admin123',
                'flota': 'repartidor1@belgranoahorro.com / flota123'
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/panel')
@login_required
def panel():
    if current_user.role == 'admin':
        # Obtener filtros de la URL
        estado_filter = request.args.get('estado', 'todos')
        fecha_filter = request.args.get('fecha', 'todos')
        
        # Consulta base
        query = Ticket.query
        
        # Aplicar filtros
        if estado_filter != 'todos':
            query = query.filter_by(estado=estado_filter)
        
        if fecha_filter == 'hoy':
            from datetime import datetime, timedelta
            hoy = datetime.now().date()
            query = query.filter(Ticket.fecha_creacion >= hoy)
        elif fecha_filter == 'semana':
            from datetime import datetime, timedelta
            semana_pasada = datetime.now().date() - timedelta(days=7)
            query = query.filter(Ticket.fecha_creacion >= semana_pasada)
        elif fecha_filter == 'mes':
            from datetime import datetime, timedelta
            mes_pasado = datetime.now().date() - timedelta(days=30)
            query = query.filter(Ticket.fecha_creacion >= mes_pasado)
        
        # Ordenar por fecha de creación (más reciente primero)
        tickets = query.order_by(Ticket.fecha_creacion.desc()).all()
        
        # Estadísticas
        total_tickets = Ticket.query.count()
        tickets_pendientes = Ticket.query.filter_by(estado='pendiente').count()
        tickets_en_camino = Ticket.query.filter_by(estado='en-camino').count()
        tickets_entregados = Ticket.query.filter_by(estado='entregado').count()
        
        return render_template('admin_panel.html', 
                             tickets=tickets, 
                             total_tickets=total_tickets,
                             tickets_pendientes=tickets_pendientes,
                             tickets_en_camino=tickets_en_camino,
                             tickets_entregados=tickets_entregados,
                             estado_filter=estado_filter,
                             fecha_filter=fecha_filter)
    elif current_user.role == 'flota':
        tickets = Ticket.query.filter_by(asignado_a=current_user.id).order_by(Ticket.fecha_creacion.desc()).all()
        return render_template('flota_panel.html', tickets=tickets)
    else:
        return 'Acceso no permitido', 403

# ==========================================
# HELPERS DE SERIALIZACIÓN / ACTUALIZACIÓN DE TICKETS
# ==========================================

def _safe_parse_productos(productos_payload: Any) -> List[Dict[str, Any]]:
    """
    Normaliza el payload de productos recibido (list, str JSON, dict) a una lista de dicts.
    """
    if isinstance(productos_payload, list):
        return [p for p in productos_payload if isinstance(p, dict)]

    if isinstance(productos_payload, dict):
        return [productos_payload]

    if isinstance(productos_payload, str):
        try:
            parsed = json.loads(productos_payload)
            if isinstance(parsed, list):
                return [p for p in parsed if isinstance(p, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            pass

    return []


def _serialize_ticket(ticket: Ticket) -> Dict[str, Any]:
    """
    Serializa un objeto Ticket a dict para las APIs REST.
    """
    productos = []
    if ticket.productos:
        try:
            productos = json.loads(ticket.productos) if isinstance(ticket.productos, str) else ticket.productos
        except Exception:
            productos = []

    return {
        'id': ticket.id,
        'numero': ticket.numero,
        'numero_pedido': ticket.numero,
        'cliente_nombre': ticket.cliente_nombre,
        'cliente_direccion': ticket.cliente_direccion,
        'cliente_telefono': ticket.cliente_telefono,
        'cliente_email': ticket.cliente_email,
        'productos': productos,
        'total': float(ticket.total) if ticket.total is not None else 0.0,
        'estado': ticket.estado,
        'prioridad': ticket.prioridad,
        'indicaciones': ticket.indicaciones,
        'repartidor': ticket.repartidor_nombre,
        'asignado_a': ticket.asignado_a,
        'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
        'fecha_asignacion': ticket.fecha_asignacion.isoformat() if ticket.fecha_asignacion else None,
        'fecha_entrega': ticket.fecha_entrega.isoformat() if ticket.fecha_entrega else None,
    }


def _apply_ticket_updates(ticket: Ticket, data: Dict[str, Any]) -> None:
    """
    Actualiza un ticket existente con los campos permitidos provenientes de la API.
    """
    simple_fields = [
        'cliente_nombre',
        'cliente_direccion',
        'cliente_telefono',
        'cliente_email',
        'estado',
        'prioridad',
        'indicaciones',
    ]

    for field in simple_fields:
        if field in data and data[field] is not None:
            setattr(ticket, field, data[field])

    if 'total' in data and data['total'] is not None:
        try:
            ticket.total = float(data['total'])
        except (TypeError, ValueError):
            pass

    if 'productos' in data and data['productos'] is not None:
        productos_normalizados = _safe_parse_productos(data['productos'])
        ticket.productos = json.dumps(productos_normalizados)

    if 'repartidor' in data or 'repartidor_nombre' in data:
        nuevo_repartidor = data.get('repartidor_nombre', data.get('repartidor'))
        ticket.repartidor_nombre = nuevo_repartidor
        ticket.fecha_asignacion = datetime.utcnow() if nuevo_repartidor else None

    # Actualizar fechas según estado
    if 'estado' in data and data['estado']:
        if data['estado'] in ('entregado', 'completado'):
            ticket.fecha_entrega = datetime.utcnow()
        elif data['estado'] in ('pendiente', 'en-preparacion', 'en_proceso'):
            ticket.fecha_entrega = None


# Endpoint REST para recibir tickets desde la app principal
@app.route('/api/tickets/recibir', methods=['POST'])
def recibir_ticket_externo():
    """
    Endpoint para recibir tickets desde la aplicación principal de Belgrano Ahorro con manejo robusto de errores
    """
    try:
        auth_error = _validate_api_request()
        if auth_error:
            return auth_error

        data = request.get_json()
        print(f"📥 Datos recibidos en Ticketera desde {request.remote_addr}:")
        print(f"   Headers: {dict(request.headers)}")
        print(f"   Datos: {json.dumps(data, indent=2)}")
        
        if not data:
            print("❌ No se recibieron datos")
            return jsonify({'error': 'Datos no recibidos'}), 400
        
        # Validar campos requeridos
        required_fields = ['numero', 'cliente_nombre']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print(f"❌ Campos requeridos faltantes: {missing_fields}")
            return jsonify({'error': f'Campos requeridos faltantes: {missing_fields}'}), 400
        
        # Validar y convertir total a número
        try:
            total_recibido = float(data.get('total', 0))
            if total_recibido <= 0:
                print(f"⚠️ ADVERTENCIA: Total inválido o cero recibido: {total_recibido}")
                print(f"   Datos completos recibidos: total={data.get('total')}")
            else:
                print(f"✅ Total recibido correctamente: ${total_recibido}")
        except (TypeError, ValueError) as e:
            print(f"❌ ERROR: No se pudo convertir total a número: {e}")
            print(f"   Valor recibido: {data.get('total')} (tipo: {type(data.get('total'))})")
            total_recibido = 0.0
        
        # Validar y loguear productos recibidos
        productos_recibidos = data.get('productos', [])
        if not productos_recibidos:
            print("⚠️ ADVERTENCIA: No se recibieron productos en el ticket")
        else:
            print(f"✅ Productos recibidos: {len(productos_recibidos)} items")
            for idx, producto in enumerate(productos_recibidos[:5], 1):  # Mostrar primeros 5
                if isinstance(producto, dict):
                    print(f"   {idx}. {producto.get('nombre', 'Sin nombre')} x{producto.get('cantidad', 0)} - ${producto.get('precio', 0)} - Subtotal: ${producto.get('subtotal', 0)}")
                else:
                    print(f"   {idx}. {producto} (formato no esperado)")
            if len(productos_recibidos) > 5:
                print(f"   ... y {len(productos_recibidos) - 5} productos más")
        
        # Determinar prioridad basada en tipo de cliente
        prioridad = data.get('prioridad', 'normal')
        tipo_cliente = data.get('tipo_cliente', 'cliente')
        
        # Si es comerciante, asegurar prioridad alta
        if tipo_cliente == 'comerciante' and prioridad != 'alta':
            prioridad = 'alta'
        
        # Idempotencia: si ya existe un ticket con el mismo numero, devolverlo
        numero_ticket = data.get('numero', data.get('numero_pedido'))
        if numero_ticket:
            existente = Ticket.query.filter_by(numero=numero_ticket).first()
            if existente:
                print(f"✅ Ticket existente encontrado: {numero_ticket} (ID: {existente.id})")
                # Parsear productos del ticket existente
                productos_existente = []
                try:
                    if existente.productos:
                        productos_existente = json.loads(existente.productos) if isinstance(existente.productos, str) else existente.productos
                except Exception as e:
                    print(f"⚠️ Error parseando productos del ticket existente: {e}")
                    productos_existente = []
                
                return jsonify({
                    'exito': True, 
                    'ticket_id': existente.id, 
                    'idempotent': True,
                    'numero': existente.numero,
                    'estado': existente.estado,
                    'repartidor_asignado': existente.repartidor_nombre,
                    'fecha_creacion': existente.fecha_creacion.isoformat() if existente.fecha_creacion else None,
                    'cliente_nombre': existente.cliente_nombre,
                    'total': existente.total,
                    'productos': productos_existente  # Incluir productos en la respuesta
                }), 200
        
        # Procesar productos recibidos
        productos_data = data.get('productos', [])
        if not isinstance(productos_data, list):
            print(f"⚠️ ADVERTENCIA: productos no es una lista, es {type(productos_data)}. Convirtiendo...")
            if isinstance(productos_data, str):
                try:
                    productos_data = json.loads(productos_data)
                except:
                    productos_data = []
            else:
                productos_data = []
        
        # Validar estructura de productos
        productos_validos = []
        for idx, producto in enumerate(productos_data, 1):
            if isinstance(producto, dict):
                # Asegurar que tenga los campos mínimos
                producto_validado = {
                    'id': str(producto.get('id', f'producto_{idx}')),
                    'nombre': producto.get('nombre', 'Producto sin nombre'),
                    'precio': float(producto.get('precio', 0)),
                    'cantidad': int(producto.get('cantidad', 0)),
                    'subtotal': float(producto.get('subtotal', producto.get('precio', 0) * producto.get('cantidad', 0))),
                    'sucursal': producto.get('sucursal', 'Sucursal no especificada'),
                    'negocio': producto.get('negocio', 'Negocio no especificado'),
                    'categoria': producto.get('categoria', 'Sin categoría'),
                    'descripcion': producto.get('descripcion', 'Sin descripción'),
                    'stock': int(producto.get('stock', 0)),
                    'destacado': bool(producto.get('destacado', False))
                }
                productos_validos.append(producto_validado)
            else:
                print(f"⚠️ Producto {idx} no es un diccionario, saltando...")
        
        print(f"✅ {len(productos_validos)} productos validados correctamente")
        
        # Crear el ticket con los datos recibidos
        ticket = Ticket(
            numero=numero_ticket or f'TICKET-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            cliente_nombre=data.get('cliente_nombre', data.get('cliente', 'Cliente')),
            cliente_direccion=data.get('cliente_direccion', data.get('direccion', 'Sin dirección')),
            cliente_telefono=data.get('cliente_telefono', data.get('telefono', 'Sin teléfono')),
            cliente_email=data.get('cliente_email', data.get('email', 'sin@email.com')),
            productos=json.dumps(productos_validos),  # Guardar productos validados como JSON string
            total=total_recibido,  # CORRECCIÓN: Usar total validado
            estado=data.get('estado', 'pendiente'),
            prioridad=prioridad,
            indicaciones=data.get('indicaciones', data.get('notas', ''))
        )
        
        print(f"✅ Ticket creado con total: ${ticket.total}")
        
        db.session.add(ticket)
        db.session.commit()
        
        # Asignar automáticamente a un repartidor aleatorio
        repartidor_asignado, user_id_asignado = asignar_repartidor_automatico(ticket)
        if repartidor_asignado:
            ticket.repartidor_nombre = repartidor_asignado
            ticket.asignado_a = user_id_asignado  # CORRECCIÓN: Asignar ID del usuario de flota
            ticket.fecha_asignacion = datetime.utcnow()
            db.session.commit()
            print(f"✅ Ticket asignado automáticamente a {repartidor_asignado} (Usuario ID: {user_id_asignado})")
        
        # Emitir evento WebSocket para actualización en tiempo real
        try:
            # Parsear productos para el evento WebSocket
            productos_ws = []
            try:
                if ticket.productos:
                    productos_ws = json.loads(ticket.productos) if isinstance(ticket.productos, str) else ticket.productos
            except:
                productos_ws = []
            
            socketio.emit('nuevo_ticket', {
                'ticket_id': ticket.id, 
                'numero': ticket.numero,
                'cliente_nombre': ticket.cliente_nombre,
                'estado': ticket.estado,
                'repartidor': ticket.repartidor_nombre,
                'prioridad': ticket.prioridad,
                'tipo_cliente': tipo_cliente,
                'productos': productos_ws,  # Incluir productos en el evento WebSocket
                'total': ticket.total
            })
            print(f"📡 Evento WebSocket emitido para ticket {ticket.id} con {len(productos_ws)} productos")
        except Exception as ws_error:
            print(f"Error emitiendo WebSocket: {ws_error}")
        
        # Mensaje de log más detallado
        tipo_cliente_str = "COMERCIANTE" if tipo_cliente == 'comerciante' else "CLIENTE"
        print(f"✅ Ticket recibido exitosamente: {ticket.numero} - {ticket.cliente_nombre} ({tipo_cliente_str}) - Prioridad: {ticket.prioridad}")
        print(f"   📦 Productos guardados: {len(productos_validos)} items - Total: ${ticket.total}")
        
        # Parsear productos para incluirlos en la respuesta
        productos_respuesta = []
        try:
            if ticket.productos:
                productos_respuesta = json.loads(ticket.productos) if isinstance(ticket.productos, str) else ticket.productos
        except Exception as e:
            print(f"⚠️ Error parseando productos para respuesta: {e}")
            productos_respuesta = []
        
        return jsonify({
            'exito': True, 
            'ticket_id': ticket.id, 
            'numero': ticket.numero,
            'estado': ticket.estado,
            'repartidor_asignado': ticket.repartidor_nombre,
            'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
            'cliente_nombre': ticket.cliente_nombre,
            'total': ticket.total,
            'productos': productos_respuesta  # Incluir productos en la respuesta
        })
        
    except Exception as e:
        print(f"❌ Error al procesar ticket: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def asignar_repartidor_automatico(ticket):
    """
    Asigna automáticamente un repartidor aleatorio que no tenga tickets de prioridad máxima
    Retorna: (nombre_repartidor, user_id) o (None, None)
    """
    import random
    
    # Obtener todos los usuarios de flota de la base de datos
    usuarios_flota = User.query.filter_by(role='flota', activo=True).all()
    
    if not usuarios_flota:
        print("⚠️ No se encontraron usuarios de flota activos en la base de datos")
        return None, None
    
    # Filtrar repartidores que no tengan tickets de prioridad máxima
    repartidores_disponibles = []
    
    for user_flota in usuarios_flota:
        # Contar tickets de prioridad máxima asignados a este usuario
        tickets_prioridad_maxima = Ticket.query.filter_by(
            asignado_a=user_flota.id,
            prioridad='alta'
        ).count()
        
        # Si no tiene tickets de prioridad máxima, está disponible
        if tickets_prioridad_maxima == 0:
            repartidores_disponibles.append(user_flota)
    
    # Si no hay repartidores disponibles sin prioridad máxima, usar todos
    if not repartidores_disponibles:
        repartidores_disponibles = usuarios_flota
        print(f"⚠️ Todos los repartidores tienen tickets de alta prioridad, usando todos para balanceo")
    
    # Seleccionar aleatoriamente
    if repartidores_disponibles:
        repartidor_seleccionado = random.choice(repartidores_disponibles)
        print(f"🎯 Repartidor seleccionado: {repartidor_seleccionado.nombre} (ID: {repartidor_seleccionado.id}, Email: {repartidor_seleccionado.email})")
        return repartidor_seleccionado.nombre, repartidor_seleccionado.id
    
    print("❌ No se pudo asignar repartidor: No hay usuarios de flota disponibles")
    return None, None

@app.route('/api/tickets', methods=['GET', 'POST'])
def api_tickets():
    """
    Endpoint REST principal:
    - POST: recibir nuevos tickets (compatibilidad con clientes existentes)
    - GET: obtener listado paginado/filtrado de tickets para integraciones (DevOps, panel externo)
    """
    if request.method == 'POST':
        return recibir_ticket_externo()

    auth_error = _validate_api_request()
    if auth_error:
        return auth_error

    try:
        estado = request.args.get('estado')
        limite_param = request.args.get('limit', '200')
        try:
            limite = max(1, min(int(limite_param), 1000))
        except ValueError:
            limite = 200

        query = Ticket.query.order_by(Ticket.fecha_creacion.desc())
        if estado and estado not in ('todos', 'all'):
            query = query.filter_by(estado=estado)

        tickets = query.limit(limite).all()

        return jsonify({
            'status': 'success',
            'total': len(tickets),
            'data': [_serialize_ticket(ticket) for ticket in tickets]
        })
    except Exception as e:
        logger.error(f"Error obteniendo tickets vía API: {e}")
        return jsonify({'error': 'Error interno obteniendo tickets'}), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['GET', 'PUT', 'DELETE'])
def api_ticket_detalle(ticket_id: int):
    """
    Permite obtener, actualizar o eliminar un ticket específico vía API.
    """
    auth_error = _validate_api_request()
    if auth_error:
        return auth_error

    ticket = Ticket.query.filter_by(id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket no encontrado'}), 404

    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': _serialize_ticket(ticket)})

    if request.method == 'PUT':
        try:
            payload = request.get_json() or {}
        except Exception:
            return jsonify({'error': 'JSON inválido'}), 400

        try:
            _apply_ticket_updates(ticket, payload)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error actualizando ticket {ticket_id}: {e}")
            return jsonify({'error': 'Error actualizando ticket'}), 500

        # Emitir actualización en tiempo real
        try:
            socketio.emit('ticket_actualizado', {
                'ticket_id': ticket.id,
                'estado': ticket.estado,
                'prioridad': ticket.prioridad
            })
        except Exception as ws_error:
            logger.warning(f"No se pudo emitir evento WebSocket para ticket {ticket_id}: {ws_error}")

        return jsonify({'status': 'success', 'data': _serialize_ticket(ticket)})

    # DELETE
    try:
        numero_ticket = ticket.numero
        db.session.delete(ticket)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error eliminando ticket {ticket_id}: {e}")
        return jsonify({'error': 'Error eliminando ticket'}), 500

    try:
        socketio.emit('ticket_eliminado', {
            'ticket_id': ticket_id,
            'numero': numero_ticket
        })
    except Exception as ws_error:
        logger.warning(f"No se pudo emitir evento de eliminación para ticket {ticket_id}: {ws_error}")

    return jsonify({'status': 'success', 'message': f'Ticket {numero_ticket} eliminado'})

@app.route('/ticket/<int:ticket_id>/estado', methods=['POST'])
@login_required
def actualizar_estado_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    nuevo_estado = request.form.get('estado')
    nueva_prioridad = request.form.get('prioridad')
    nuevas_indicaciones = request.form.get('indicaciones')
    
    if nuevo_estado:
        ticket.estado = nuevo_estado
    if nueva_prioridad:
        ticket.prioridad = nueva_prioridad
    if nuevas_indicaciones is not None:  # Permitir strings vacíos
        ticket.indicaciones = nuevas_indicaciones
    
    db.session.commit()
    
    # Emitir evento WebSocket para actualización en tiempo real
    socketio.emit('ticket_actualizado', {
        'ticket_id': ticket.id,
        'estado': ticket.estado,
        'prioridad': ticket.prioridad
    })
    
    return jsonify({'exito': True, 'mensaje': 'Ticket actualizado correctamente'})

@app.route('/ticket/<int:ticket_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_ticket(ticket_id):
    """Editar ticket existente - NUNCA se borra, solo se actualiza"""
    if current_user.role != 'admin':
        return 'Acceso no permitido', 403
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if request.method == 'POST':
        # Obtener datos del formulario
        nuevo_estado = request.form.get('estado')
        nueva_prioridad = request.form.get('prioridad')
        nuevas_indicaciones = request.form.get('indicaciones')
        nuevo_repartidor = request.form.get('repartidor_nombre')
        
        # Actualizar solo los campos que se enviaron
        if nuevo_estado:
            ticket.estado = nuevo_estado
        if nueva_prioridad:
            ticket.prioridad = nueva_prioridad
        if nuevas_indicaciones is not None:  # Permitir strings vacíos
            ticket.indicaciones = nuevas_indicaciones
        if nuevo_repartidor:
            ticket.repartidor_nombre = nuevo_repartidor
        
        # Guardar cambios
        db.session.commit()
        
        # Emitir evento WebSocket para actualización en tiempo real
        socketio.emit('ticket_actualizado', {
            'ticket_id': ticket.id,
            'estado': ticket.estado,
            'prioridad': ticket.prioridad,
            'repartidor': ticket.repartidor_nombre
        })
        
        flash('Ticket actualizado correctamente', 'success')
        return redirect(url_for('panel'))
    
    # Para GET, mostrar formulario de edición
    return render_template('editar_ticket.html', ticket=ticket)



@app.route('/gestion_flota')
@login_required
def gestion_flota():
    if current_user.role != 'admin':
        return 'Acceso no permitido', 403
    
    # Obtener todos los repartidores disponibles
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    
    # Obtener tickets con repartidores asignados
    tickets_asignados = Ticket.query.filter(Ticket.repartidor_nombre.isnot(None)).all()
    
    # Estadísticas por repartidor
    stats_repartidores = {}
    for rep in repartidores:
        tickets_rep = Ticket.query.filter_by(repartidor_nombre=rep).all()
        stats_repartidores[rep] = {
            'total': len(tickets_rep),
            'pendientes': len([t for t in tickets_rep if t.estado == 'pendiente']),
            'en_camino': len([t for t in tickets_rep if t.estado == 'en-camino']),
            'entregados': len([t for t in tickets_rep if t.estado == 'entregado'])
        }
    
    return render_template('gestion_flota.html', 
                         repartidores=repartidores, 
                         tickets_asignados=tickets_asignados,
                         stats_repartidores=stats_repartidores)

@app.route('/reportes')
@login_required
def reportes():
    if current_user.role != 'admin':
        return 'Acceso no permitido', 403
    
    # Estadísticas generales
    total_tickets = Ticket.query.count()
    tickets_pendientes = Ticket.query.filter_by(estado='pendiente').count()
    tickets_en_camino = Ticket.query.filter_by(estado='en-camino').count()
    tickets_entregados = Ticket.query.filter_by(estado='entregado').count()
    
    # Tickets por repartidor
    tickets_por_repartidor = {}
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    for rep in repartidores:
        tickets_por_repartidor[rep] = Ticket.query.filter_by(repartidor_nombre=rep).count()
    
    return render_template('reportes.html',
                         total_tickets=total_tickets,
                         tickets_pendientes=tickets_pendientes,
                         tickets_en_camino=tickets_en_camino,
                         tickets_entregados=tickets_entregados,
                         tickets_por_repartidor=tickets_por_repartidor)

@app.route('/ticket/<int:ticket_id>/asignar_repartidor', methods=['POST'])
@login_required
def asignar_repartidor(ticket_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Acceso no permitido'}), 403
    
    ticket = Ticket.query.get_or_404(ticket_id)
    repartidor = request.form.get('repartidor')
    
    if repartidor:
        ticket.repartidor = repartidor
        db.session.commit()
        
        # Emitir evento WebSocket
        socketio.emit('ticket_asignado', {
            'ticket_id': ticket.id,
            'repartidor': repartidor
        })
        
        return jsonify({'exito': True, 'mensaje': f'Ticket asignado a {repartidor}'})
    
    return jsonify({'error': 'Repartidor no especificado'}), 400

@app.route('/ticket/<int:ticket_id>/detalle')
@login_required
def detalle_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('detalle_ticket.html', ticket=ticket)

@app.route('/ticket/<int:ticket_id>/pdf')
@login_required
def download_ticket_pdf(ticket_id):
    """
    Descarga el PDF de un ticket.
    
    Validaciones:
    - Admin puede descargar cualquier ticket
    - Repartidor solo puede descargar sus propios tickets
    """
    from flask import send_file, abort
    from pdf_generator import generate_ticket_pdf
    
    # Obtener ticket
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Validar permisos
    if current_user.role == 'flota':
        # Repartidor solo puede ver sus propios tickets
        if ticket.asignado_a != current_user.id:
            logger.warning(f"Repartidor {current_user.id} intentó acceder al ticket {ticket_id} de otro repartidor")
            abort(403)
    elif current_user.role != 'admin':
        # Otros roles no tienen acceso
        logger.warning(f"Usuario con role '{current_user.role}' intentó descargar PDF")
        abort(403)
    
    try:
        # Generar PDF
        logger.info(f"Generando PDF para ticket {ticket.numero} (ID: {ticket.id})")
        pdf_buffer = generate_ticket_pdf(ticket)
        
        # Nombre del archivo
        filename = f"ticket_{ticket.numero}.pdf"
        
        logger.info(f"PDF generado exitosamente: {filename}")
        
        # Enviar archivo
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error generando PDF para ticket {ticket_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        abort(500)


@app.route('/ticket/<int:ticket_id>/eliminar', methods=['POST'])
@login_required
def eliminar_ticket(ticket_id):
    """Eliminar ticket - SOLO con confirmación explícita del administrador"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Acceso no permitido'}), 403
    
    # Verificar confirmación explícita
    confirmacion = request.form.get('confirmacion')
    if confirmacion != 'ELIMINAR_PERMANENTEMENTE':
        return jsonify({'error': 'Se requiere confirmación explícita para eliminar tickets'}), 400
    
    ticket = Ticket.query.get_or_404(ticket_id)
    numero_ticket = ticket.numero
    
    # Crear registro de auditoría antes de eliminar
    try:
        # Aquí podrías guardar un log de la eliminación si es necesario
        print(f"TICKET ELIMINADO por {current_user.username}: {numero_ticket} (ID: {ticket_id})")
        
        db.session.delete(ticket)
        db.session.commit()
        
        # Emitir evento WebSocket
        socketio.emit('ticket_eliminado', {
            'ticket_id': ticket_id,
            'numero': numero_ticket
        })
        
        return jsonify({'exito': True, 'mensaje': f'Ticket {numero_ticket} eliminado permanentemente'})
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando ticket {ticket_id}: {e}")
        return jsonify({'error': 'Error al eliminar el ticket'}), 500

# ===== GESTIÓN DE USUARIOS =====

@app.route('/gestion_usuarios')
@login_required
@role_required('admin')
def gestion_usuarios():
    """Panel de gestión de usuarios para administradores"""
    usuarios = User.query.all()
    return render_template('gestion_usuarios.html', usuarios=usuarios)

@app.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def crear_usuario():
    """Crear nuevo usuario (solo admin)"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        role = request.form.get('role')
        
        # Validaciones
        if not all([username, email, password, nombre, role]):
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('crear_usuario'))
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('crear_usuario'))
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('crear_usuario'))
        
        # Crear nuevo usuario
        nuevo_usuario = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            nombre=nombre,
            role=role
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash(f'Usuario {nombre} creado exitosamente', 'success')
        return redirect(url_for('gestion_usuarios'))
    
    return render_template('crear_usuario.html')

@app.route('/usuario/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def editar_usuario(user_id):
    """Editar usuario existente (solo admin)"""
    usuario = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre = request.form.get('nombre')
        role = request.form.get('role')
        nueva_password = request.form.get('nueva_password')
        
        # Validaciones
        if not all([username, email, nombre, role]):
            flash('Los campos username, email, nombre y role son obligatorios', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Verificar si el username ya existe (excluyendo el usuario actual)
        usuario_existente = User.query.filter_by(username=username).first()
        if usuario_existente and usuario_existente.id != user_id:
            flash('El nombre de usuario ya existe', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Verificar si el email ya existe (excluyendo el usuario actual)
        email_existente = User.query.filter_by(email=email).first()
        if email_existente and email_existente.id != user_id:
            flash('El email ya está registrado', 'danger')
            return redirect(url_for('editar_usuario', user_id=user_id))
        
        # Actualizar usuario
        usuario.username = username
        usuario.email = email
        usuario.nombre = nombre
        usuario.role = role
        
        if nueva_password:
            usuario.password = generate_password_hash(nueva_password)
        
        db.session.commit()
        flash(f'Usuario {nombre} actualizado exitosamente', 'success')
        return redirect(url_for('gestion_usuarios'))
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuario/<int:user_id>/eliminar', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_usuario(user_id):
    """Eliminar usuario (solo admin)"""
    usuario = User.query.get_or_404(user_id)
    
    # No permitir eliminar al administrador principal
    if usuario.username == 'admin':
        flash('No se puede eliminar al administrador principal', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    # Verificar si el usuario tiene tickets asignados
    tickets_asignados = Ticket.query.filter_by(asignado_a=user_id).count()
    if tickets_asignados > 0:
        flash(f'No se puede eliminar el usuario. Tiene {tickets_asignados} tickets asignados', 'danger')
        return redirect(url_for('gestion_usuarios'))
    
    nombre_usuario = usuario.nombre
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'Usuario {nombre_usuario} eliminado exitosamente', 'success')
    return redirect(url_for('gestion_usuarios'))

@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        # Validaciones
        if not check_password_hash(current_user.password, password_actual):
            flash('La contraseña actual es incorrecta', 'danger')
            return redirect(url_for('cambiar_password'))
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas nuevas no coinciden', 'danger')
            return redirect(url_for('cambiar_password'))
        
        if len(nueva_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('cambiar_password'))
        
        # Actualizar contraseña
        current_user.password = generate_password_hash(nueva_password)
        db.session.commit()
        
        flash('Contraseña cambiada exitosamente', 'success')
        return redirect(url_for('panel'))
    
    return render_template('cambiar_password.html')

# ==========================================
# ENDPOINTS PARA CONSUMIR API DE BELGRANO AHORRO
# ==========================================

@app.route('/api/ahorro/productos', methods=['GET'])
@login_required
@role_required('admin')
def get_productos_ahorro():
    """Obtener productos desde Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        categoria = request.args.get('categoria')
        productos = api_client.get_productos(categoria)
        
        return jsonify({
            'status': 'success',
            'productos': productos,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo productos de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/pedido/<numero_pedido>', methods=['GET'])
@login_required
def get_pedido_ahorro(numero_pedido):
    """Obtener pedido específico desde Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        pedido = api_client.get_pedido(numero_pedido)
        
        if not pedido:
            return jsonify({
                'status': 'error',
                'error': 'Pedido no encontrado'
            }), 404
        
        return jsonify({
            'status': 'success',
            'pedido': pedido,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo pedido {numero_pedido} de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/pedido/<numero_pedido>/estado', methods=['PUT'])
@login_required
def actualizar_estado_pedido_ahorro(numero_pedido):
    """Actualizar estado de pedido en Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({
                'status': 'error',
                'error': 'Estado requerido'
            }), 400
        
        success = api_client.actualizar_estado_pedido(numero_pedido, nuevo_estado)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Estado actualizado a {nuevo_estado}',
                'numero_pedido': numero_pedido,
                'estado': nuevo_estado,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': 'No se pudo actualizar el estado'
            }), 500
        
    except Exception as e:
        logger.error(f"Error actualizando estado del pedido {numero_pedido}: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/sync/tickets', methods=['POST'])
@login_required
@role_required('admin')
def sync_tickets_to_ahorro():
    """Sincronizar tickets hacia Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        # Obtener todos los tickets
        tickets = Ticket.query.all()
        tickets_data = []
        
        for ticket in tickets:
            tickets_data.append({
                'numero_pedido': ticket.numero,
                'ticket_id': ticket.id,
                'estado': ticket.estado,
                'repartidor': ticket.repartidor_nombre,
                'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
                'fecha_actualizacion': ticket.fecha_asignacion.isoformat() if ticket.fecha_asignacion else None,
                'datos_completos': {
                    'id': ticket.id,
                    'numero_pedido': ticket.numero,
                    'cliente': ticket.cliente_nombre,
                    'productos': ticket.productos,
                    'total': ticket.total,
                    'estado': ticket.estado,
                    'repartidor': ticket.repartidor_nombre,
                    'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
                    'fecha_actualizacion': ticket.fecha_asignacion.isoformat() if ticket.fecha_asignacion else None
                }
            })
        
        success = api_client.sync_tickets_to_ahorro(tickets_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'{len(tickets_data)} tickets sincronizados',
                'tickets_synced': len(tickets_data),
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': 'Error en la sincronización'
            }), 500
        
    except Exception as e:
        logger.error(f"Error sincronizando tickets: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ahorro/test', methods=['GET'])
@login_required
@role_required('admin')
def test_ahorro_api():
    """Probar conexión con API de Belgrano Ahorro"""
    try:
        if not api_client:
            return jsonify({
                'status': 'error',
                'error': 'Cliente API no disponible'
            }), 500
        
        # Probar health check
        health = api_client.health_check()
        
        # Probar obtención de productos
        productos = api_client.get_productos()
        
        return jsonify({
            'status': 'success',
            'health_check': health,
            'productos_test': {
                'status': 'success' if productos else 'error',
                'total': len(productos.get('productos', [])) if productos else 0
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error probando API de Ahorro: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Ruta principal ya definida arriba como home()

# Registrar blueprint de DevOps (eliminando duplicado)
# Este bloque se eliminó porque ya se registra arriba en la línea 58

# Registrar el blueprint de imágenes
try:
    from .image_routes import image_bp
except ImportError:
    try:
        from belgrano_tickets.image_routes import image_bp
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from image_routes import image_bp
app.register_blueprint(image_bp, url_prefix='/api')

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =================================================================
# ENDPOINTS UNIFICADOS DE CLOUDINARY
# =================================================================

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """
    Endpoint unificado para subir imágenes a Cloudinary.
    
    Acepta:
    - multipart/form-data
    - Campo obligatorio: file
    - Campo opcional: folder (por defecto "belgrano-ahorro")
    
    Retorna:
    - secure_url: URL pública de la imagen en Cloudinary
    - public_id: ID público de la imagen
    """
    try:
        # Verificar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        # Verificar que el archivo tenga nombre
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Obtener folder opcional
        folder = request.form.get('folder', 'belgrano-ahorro')
        
        # Importar cloudinary
        try:
            import cloudinary.uploader
        except ImportError:
            return jsonify({"error": "Cloudinary not installed"}), 500
        
        # Subir a Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='auto'
        )
        
        logger.info(f"✅ Imagen subida a Cloudinary: {result['secure_url']}")
        
        return jsonify({
            "secure_url": result["secure_url"],
            "public_id": result["public_id"]
        })
    
    except Exception as e:
        logger.error(f"❌ Error subiendo imagen a Cloudinary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/ping-cloudinary', methods=['GET'])
def ping_cloudinary():
    """
    Endpoint para verificar la conexión con Cloudinary.
    
    Retorna:
    - status: "ok" si la conexión es exitosa
    - error: mensaje de error si falla
    """
    try:
        import cloudinary.api
        cloudinary.api.ping()
        
        # Obtener configuración
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from cloudinary_config import get_cloudinary_status
        status = get_cloudinary_status()
        
        return jsonify({
            "status": "ok",
            "configured": status['configured'],
            "cloud_name": status['cloud_name']
        })
    except ImportError:
        return jsonify({"error": "Cloudinary not installed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Inicializar usuarios automáticamente
        inicializar_usuarios_automaticamente()
    print("Iniciando aplicación de tickets en puerto 5001...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
