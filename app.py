import os
from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify, session
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_socketio import SocketIO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import logging
import hmac
import binascii
import hashlib

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Configuración de base de datos - usar variable de entorno si existe, si no, ruta absoluta
import os
env_db_path = os.environ.get('TICKETS_DB_PATH')
db_path = env_db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'belgrano_tickets.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print(f"🗄️ Ticketera DB_PATH: {db_path}")

# Importar db desde models
try:
    from models import db, User, Ticket
except ImportError:
    try:
        # Fallback para importación desde belgrano_tickets
        from belgrano_tickets.models import db, User, Ticket
    except ImportError:
        # Fallback final: importación absoluta
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import db, User, Ticket

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
        print("ℹ️ BELGRANO_AHORRO_URL no configurada (normal en desarrollo)")
    else:
        print("⚠️ Variable de entorno BELGRANO_AHORRO_URL no está definida")

if not BELGRANO_AHORRO_API_KEY:
    if env_status != 'production':
        print("ℹ️ BELGRANO_AHORRO_API_KEY no configurada (normal en desarrollo)")
    else:
        print("⚠️ Variable de entorno BELGRANO_AHORRO_API_KEY no está definida")

print(f"🔗 Configuración API:")
print(f"   BELGRANO_AHORRO_URL: {BELGRANO_AHORRO_URL or 'No configurada'}")
if BELGRANO_AHORRO_API_KEY:
    print(f"   API_KEY: {BELGRANO_AHORRO_API_KEY[:10]}...")
else:
    print("   API_KEY: No configurada")

# ==========================================

# Importar cliente API
try:
    from belgrano_tickets.api_client import create_api_client, test_api_connection
    if BELGRANO_AHORRO_URL and BELGRANO_AHORRO_API_KEY:
        api_client = create_api_client(BELGRANO_AHORRO_URL, BELGRANO_AHORRO_API_KEY)
        print("Cliente API de Belgrano Ahorro inicializado")
    else:
        print("⚠️ Variables de entorno BELGRANO_AHORRO_URL o BELGRANO_AHORRO_API_KEY no configuradas")
        api_client = None
except ImportError as e:
    print(f"No se pudo inicializar el cliente API: {e}")
    api_client = None

# Importar blueprint de DevOps con ruta robusta
try:
    # Intento directo si el cwd es la raíz del proyecto
    from devops_routes import devops_bp
    app.register_blueprint(devops_bp)
    print("Blueprint de DevOps registrado (import directo)")
except Exception as e:
    try:
        # Añadir la raíz del proyecto al sys.path y reintentar
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from devops_routes import devops_bp as devops_bp_root
        app.register_blueprint(devops_bp_root)
        print("Blueprint de DevOps registrado (import con sys.path raíz)")
    except Exception as e2:
        # Fallback: cargar por ruta absoluta con importlib
        try:
            import importlib.util
            devops_path = os.path.join(project_root, 'devops_routes.py')
            spec = importlib.util.spec_from_file_location('devops_routes', devops_path)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            devops_bp_dynamic = getattr(module, 'devops_bp', None)
            if devops_bp_dynamic is not None:
                app.register_blueprint(devops_bp_dynamic)
                print("Blueprint de DevOps registrado (importlib por ruta)")
            else:
                print("No se encontró devops_bp en devops_routes.py (importlib)")
        except Exception as e3:
            print(f"❌ No se pudo registrar el blueprint de DevOps: {e3}")
            # Verificar si el archivo existe
            if os.path.exists(devops_path):
                print(f"✅ Archivo devops_routes.py existe en: {devops_path}")
            else:
                print(f"❌ Archivo devops_routes.py NO existe en: {devops_path}")
                # Listar archivos en el directorio
                try:
                    files = os.listdir(project_root)
                    print(f"📁 Archivos en {project_root}: {files}")
                except:
                    print("❌ No se puede listar archivos del directorio")

# Inicializar db con la app
db.init_app(app)

# Crear contexto de aplicación para inicializar la base de datos
with app.app_context():
    db.create_all()
    
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
        print(f"🧭 belgrano_tickets.app rutas DevOps: {devops_rules}")
    except Exception as _e_list_devops:
        print(f"⚠️ No se pudieron listar rutas DevOps en belgrano_tickets.app: {_e_list_devops}")

    # Fallback: si no hay rutas /devops, registrar endpoints mínimos
    try:
        has_devops = any(str(r.rule).startswith('/devops') for r in app.url_map.iter_rules())
        if not has_devops:
            @app.route('/devops/')
            def _devops_fallback_home():
                from flask import session, redirect, make_response
                print("🔧 Usando fallback DevOps home")
                
                # Verificar autenticación
                if not session.get('devops_authenticated'):
                    print("🔧 No autenticado, redirigiendo a login")
                    return redirect('/devops/login')
                
                # Panel principal de DevOps con funcionalidad real
                from datetime import datetime
                import os
                
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
                print("🔧 Usando fallback de DevOps login")

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
                        return jsonify({'status': 'error', 'message': 'Credenciales incorrectas'}), 401
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
                from flask import session, jsonify
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                return jsonify({
                    'status': 'success',
                    'message': 'Sistema DevOps funcionando correctamente',
                    'timestamp': '2025-01-19T01:00:00Z',
                    'version': '2.0',
                    'mode': 'fallback'
                })
            
            @app.route('/devops/status')
            def _devops_fallback_status():
                from flask import session, jsonify
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                return jsonify({
                    'status': 'success',
                    'system': 'DevOps System',
                    'state': 'active',
                    'services': {
                        'api': 'running',
                        'database': 'connected',
                        'monitoring': 'active'
                    },
                    'mode': 'fallback'
                })
            
            @app.route('/devops/info')
            def _devops_fallback_info():
                from flask import session, jsonify
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                return jsonify({
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
                })
            
            @app.route('/devops/ofertas')
            def _devops_fallback_ofertas():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Simular datos de ofertas
                        ofertas = [
                            {
                                'id': 1,
                                'titulo': 'Oferta Especial 50%',
                                'descripcion': 'Descuento del 50% en productos seleccionados',
                                'descuento': 50,
                                'fecha_inicio': '2025-01-19',
                                'fecha_fin': '2025-01-31',
                                'activa': True,
                                'negocio_id': 1
                            },
                            {
                                'id': 2,
                                'titulo': 'Oferta 2x1',
                                'descripcion': 'Lleva 2 productos y paga solo 1',
                                'descuento': 100,
                                'fecha_inicio': '2025-01-20',
                                'fecha_fin': '2025-02-15',
                                'activa': True,
                                'negocio_id': 2
                            }
                        ]
                        
                        return jsonify({
                            'status': 'success',
                            'data': {
                                'ofertas': ofertas,
                                'total': len(ofertas),
                                'timestamp': datetime.now().isoformat()
                            },
                            'source': 'simulated',
                            'message': f'Ofertas obtenidas correctamente ({len(ofertas)} encontradas)'
                        })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo ofertas: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/ofertas.html')
            
            @app.route('/devops/negocios')
            def _devops_fallback_negocios():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Simular datos de negocios
                        negocios = [
                            {
                                'id': 1,
                                'nombre': 'Supermercado Central',
                                'descripcion': 'Supermercado con productos frescos y ofertas diarias',
                                'direccion': 'Av. Belgrano 1234',
                                'telefono': '+54 11 1234-5678',
                                'email': 'info@supercentral.com',
                                'activo': True
                            },
                            {
                                'id': 2,
                                'nombre': 'Farmacia San Martín',
                                'descripcion': 'Farmacia con medicamentos y productos de salud',
                                'direccion': 'Calle San Martín 567',
                                'telefono': '+54 11 9876-5432',
                                'email': 'contacto@farmaciasanmartin.com',
                                'activo': True
                            },
                            {
                                'id': 3,
                                'nombre': 'Restaurante El Buen Sabor',
                                'descripcion': 'Restaurante con comida casera y delivery',
                                'direccion': 'Av. Corrientes 890',
                                'telefono': '+54 11 5555-1234',
                                'email': 'pedidos@elbuensabor.com',
                                'activo': True
                            }
                        ]
                        
                        return jsonify({
                            'status': 'success',
                            'data': {
                                'negocios': negocios,
                                'total': len(negocios),
                                'timestamp': datetime.now().isoformat()
                            },
                            'source': 'simulated',
                            'message': f'Negocios obtenidos correctamente ({len(negocios)} encontrados)'
                        })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo negocios: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/negocios.html')
            
            @app.route('/devops/productos')
            def _devops_fallback_productos():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Simular datos de productos
                        productos = [
                            {
                                'id': 1,
                                'nombre': 'Leche Entera 1L',
                                'descripcion': 'Leche fresca pasteurizada',
                                'precio': 850.0,
                                'categoria': 'Lácteos',
                                'stock': 50,
                                'activo': True
                            },
                            {
                                'id': 2,
                                'nombre': 'Pan Integral',
                                'descripcion': 'Pan de molde integral',
                                'precio': 450.0,
                                'categoria': 'Panadería',
                                'stock': 25,
                                'activo': True
                            }
                        ]
                        
                        return jsonify({
                            'status': 'success',
                            'data': {
                                'productos': productos,
                                'total': len(productos),
                                'timestamp': datetime.now().isoformat()
                            },
                            'source': 'simulated',
                            'message': f'Productos obtenidos correctamente ({len(productos)} encontrados)'
                        })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo productos: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/productos.html')
            
            @app.route('/devops/precios')
            def _devops_fallback_precios():
                from flask import session, jsonify, request, render_template
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    try:
                        from datetime import datetime
                        
                        # Simular datos de precios
                        precios = [
                            {
                                'id': 1,
                                'producto_id': 1,
                                'negocio_id': 1,
                                'precio': 850.0,
                                'precio_anterior': 950.0,
                                'descuento': 10.5,
                                'fecha_actualizacion': '2025-01-19',
                                'activo': True
                            },
                            {
                                'id': 2,
                                'producto_id': 2,
                                'negocio_id': 1,
                                'precio': 450.0,
                                'precio_anterior': 500.0,
                                'descuento': 10.0,
                                'fecha_actualizacion': '2025-01-19',
                                'activo': True
                            }
                        ]
                        
                        return jsonify({
                            'status': 'success',
                            'data': {
                                'precios': precios,
                                'total': len(precios),
                                'timestamp': datetime.now().isoformat()
                            },
                            'source': 'simulated',
                            'message': f'Precios obtenidos correctamente ({len(precios)} encontrados)'
                        })
                    except Exception as e:
                        return jsonify({
                            'status': 'error',
                            'message': f'Error obteniendo precios: {str(e)}',
                            'data': [],
                            'source': 'error'
                        }), 500
                
                # Si no es AJAX, devolver template HTML
                return render_template('devops/precios.html')
            
            @app.route('/devops/estadisticas')
            def _devops_fallback_estadisticas():
                from flask import session, jsonify
                if not session.get('devops_authenticated'):
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
                if not session.get('devops_authenticated'):
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
                if not session.get('devops_authenticated'):
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
                if not session.get('devops_authenticated'):
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
                if not session.get('devops_authenticated'):
                    return jsonify({'error': 'No autorizado'}), 401
                
                # Solo devolver JSON si se solicita explícitamente con todos los parámetros
                if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                    request.args.get('ajax') == 'true' and 
                    request.args.get('format') == 'json' and 
                    request.args.get('api') == 'true' and
                    request.args.get('json') == 'true'):
                    # Sincronización simulada
                    try:
                        from datetime import datetime
                        
                        # Simular proceso de sincronización
                        import time
                        time.sleep(1)  # Simular tiempo de procesamiento
                        
                        return jsonify({
                            'status': 'success',
                            'message': 'Sincronización completada exitosamente',
                            'data': {
                                'productos_sync': 25,
                                'ofertas_sync': 8,
                                'negocios_sync': 12,
                                'usuarios_sync': 45,
                                'pedidos_sync': 156,
                                'categorias_sync': 6,
                                'imagenes_sync': 89
                            },
                            'source': 'simulated',
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
                from flask import session, jsonify
                from datetime import datetime
                return jsonify({
                    'status': 'success',
                    'message': 'DevOps funcionando correctamente',
                    'timestamp': datetime.now().isoformat(),
                    'authenticated': session.get('devops_authenticated', False),
                    'mode': 'fallback'
                })
            
            @app.route('/devops/logout', methods=['GET', 'POST'])
            def _devops_fallback_logout():
                from flask import session, redirect
                session.pop('devops_authenticated', None)
                print("🔧 Logout DevOps (fallback)")
                return redirect('/devops/login')
            
            print("✅ Fallback DevOps completo registrado en belgrano_tickets.app")
    except Exception as _e_devops_fb:
        print(f"⚠️ Error registrando fallback DevOps: {_e_devops_fb}")

login_manager = LoginManager(app)

# Configuración robusta de SocketIO para evitar invalid session
socketio = SocketIO(
    app, 
    async_mode='threading',
    cors_allowed_origins="*",
    ping_timeout=30,  # Reducido para evitar timeouts
    ping_interval=10,  # Reducido para mejor estabilidad
    max_http_buffer_size=1e6,
    logger=False,
    engineio_logger=False,
    allow_upgrades=True,
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
    print(f"⚠️ Error de Socket.IO: {e}")
    # No intentar reconectar automáticamente para evitar loops
    return False

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
            except:
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

# Endpoint REST para recibir tickets desde la app principal
@app.route('/api/tickets/recibir', methods=['POST'])
def recibir_ticket_externo():
    """
    Endpoint para recibir tickets desde la aplicación principal de Belgrano Ahorro con manejo robusto de errores
    """
    try:
        # Autenticación por API Key
        api_key_header = request.headers.get('X-API-Key')
        if not api_key_header or api_key_header != BELGRANO_AHORRO_API_KEY:
            print(f"❌ API Key inválida: {api_key_header}")
            return jsonify({'error': 'API key inválida'}), 401

        data = request.get_json()
        print(f"📥 Datos recibidos en Ticketera desde {request.remote_addr}:")
        print(f"   Headers: {dict(request.headers)}")
        print(f"   Datos: {json.dumps(data, indent=2)}")
        
        if not data:
            print("❌ No se recibieron datos")
            return jsonify({'error': 'Datos no recibidos'}), 400
        
        # Validar campos requeridos
        required_fields = ['numero', 'cliente_nombre', 'total']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print(f"❌ Campos requeridos faltantes: {missing_fields}")
            return jsonify({'error': f'Campos requeridos faltantes: {missing_fields}'}), 400
        
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
                return jsonify({
                    'exito': True, 
                    'ticket_id': existente.id, 
                    'idempotent': True,
                    'numero': existente.numero,
                    'estado': existente.estado,
                    'repartidor_asignado': existente.repartidor_nombre,
                    'fecha_creacion': existente.fecha_creacion.isoformat() if existente.fecha_creacion else None,
                    'cliente_nombre': existente.cliente_nombre,
                    'total': existente.total
                }), 200
        
        # Crear el ticket con los datos recibidos
        ticket = Ticket(
            numero=numero_ticket or f'TICKET-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            cliente_nombre=data.get('cliente_nombre', data.get('cliente', 'Cliente')),
            cliente_direccion=data.get('cliente_direccion', data.get('direccion', 'Sin dirección')),
            cliente_telefono=data.get('cliente_telefono', data.get('telefono', 'Sin teléfono')),
            cliente_email=data.get('cliente_email', data.get('email', 'sin@email.com')),
            productos=json.dumps(data.get('productos', [])),
            total=data.get('total', 0),
            estado=data.get('estado', 'pendiente'),
            prioridad=prioridad,
            indicaciones=data.get('indicaciones', data.get('notas', ''))
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Asignar automáticamente a un repartidor aleatorio
        repartidor_asignado = asignar_repartidor_automatico(ticket)
        if repartidor_asignado:
            ticket.repartidor_nombre = repartidor_asignado
            db.session.commit()
            print(f"✅ Ticket asignado automáticamente a {repartidor_asignado}")
        
        # Emitir evento WebSocket para actualización en tiempo real
        try:
            socketio.emit('nuevo_ticket', {
                'ticket_id': ticket.id, 
                'numero': ticket.numero,
                'cliente_nombre': ticket.cliente_nombre,
                'estado': ticket.estado,
                'repartidor': ticket.repartidor_nombre,
                'prioridad': ticket.prioridad,
                'tipo_cliente': tipo_cliente
            })
            print(f"📡 Evento WebSocket emitido para ticket {ticket.id}")
        except Exception as ws_error:
            print(f"⚠️ Error emitiendo WebSocket: {ws_error}")
        
        # Mensaje de log más detallado
        tipo_cliente_str = "COMERCIANTE" if tipo_cliente == 'comerciante' else "CLIENTE"
        print(f"✅ Ticket recibido exitosamente: {ticket.numero} - {ticket.cliente_nombre} ({tipo_cliente_str}) - Prioridad: {ticket.prioridad}")
        
        return jsonify({
            'exito': True, 
            'ticket_id': ticket.id, 
            'numero': ticket.numero,
            'estado': ticket.estado,
            'repartidor_asignado': ticket.repartidor_nombre,
            'fecha_creacion': ticket.fecha_creacion.isoformat() if ticket.fecha_creacion else None,
            'cliente_nombre': ticket.cliente_nombre,
            'total': ticket.total
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
    """
    import random
    
    # Lista de repartidores disponibles
    repartidores = ['Repartidor1', 'Repartidor2', 'Repartidor3', 'Repartidor4', 'Repartidor5']
    
    # Filtrar repartidores que no tengan tickets de prioridad máxima
    repartidores_disponibles = []
    
    for repartidor in repartidores:
        # Contar tickets de prioridad máxima para este repartidor
        tickets_prioridad_maxima = Ticket.query.filter_by(
            repartidor_nombre=repartidor, 
            prioridad='alta'
        ).count()
        
        # Si no tiene tickets de prioridad máxima, está disponible
        if tickets_prioridad_maxima == 0:
            repartidores_disponibles.append(repartidor)
    
    # Si no hay repartidores disponibles sin prioridad máxima, usar todos
    if not repartidores_disponibles:
        repartidores_disponibles = repartidores
    
    # Seleccionar aleatoriamente
    if repartidores_disponibles:
        return random.choice(repartidores_disponibles)
    
    return None

@app.route('/api/tickets', methods=['POST'])
def recibir_ticket():
    """
    Endpoint alternativo para recibir tickets (mantener compatibilidad)
    """
    return recibir_ticket_externo()

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
        print(f"⚠️ TICKET ELIMINADO por {current_user.username}: {numero_ticket} (ID: {ticket_id})")
        
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

# Ruta principal de la aplicación
@app.route('/')
def index():
    """Página principal de la aplicación"""
    # Inicializar usuarios si es necesario
    try:
        with app.app_context():
            inicializar_usuarios_automaticamente()
    except Exception as e:
        logger.warning(f"Error inicializando usuarios: {e}")
    
    return render_template('admin_panel.html')

# Registrar blueprint de DevOps (eliminando duplicado)
# Este bloque se eliminó porque ya se registra arriba en la línea 58

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Inicializar usuarios automáticamente
        inicializar_usuarios_automaticamente()
    print("Iniciando aplicación de tickets en puerto 5001...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
